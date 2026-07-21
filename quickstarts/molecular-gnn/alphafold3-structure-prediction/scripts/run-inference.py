#!/usr/bin/env python3
"""AlphaFold 3 推論ラッパー (Docker ベース).

このスクリプトは AF3 の Python API を直接 import せず、公式の Docker イメージ経由で
run_alphafold.py を実行する薄いラッパーです。AF3 の内部 API は不安定なため、
コマンドライン境界で分離することでバージョン互換性を保ちます。

前提:
  - scripts/setup-af3.sh 実行済み
  - /mnt/af3/models/af3.bin が配置済み (Google 承認メールから取得)

使い方:
  # 通常 (MSA + 推論をまとめて実行):
  python run-inference.py \\
      --input /mnt/af3/inputs/ubiquitin_monomer.json \\
      --model-dir /mnt/af3/models \\
      --db-dir /mnt/af3/public_databases \\
      --output-dir /mnt/af3/outputs \\
      --docker-image alphafold3:v3.0.2 \\
      --jax-cache-dir ~/cloudfiles/jax-cache

  # MSA のみ (CPU 中心, ~10-15 分):
  python run-inference.py --stage msa <上と同じ>

  # 推論のみ (GPU 集中, 事前 MSA データ使用):
  python run-inference.py --stage inference \\
      --input /mnt/af3/outputs/ubiquitin_monomer/ubiquitin_monomer_data.json \\
      <他は同じ>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


def _err(msg: str, code: int = 1) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def _info(msg: str) -> None:
    print(f"[INFO] {msg}", flush=True)


def _validate_input_json(path: Path) -> None:
    """入力 JSON の必須フィールドをチェック."""
    if not path.is_file():
        _err(f"入力ファイルが見つかりません: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        _err(f"JSON パースに失敗: {path}: {e}")

    # AlphaFold Server 形式 (トップレベル配列) は AF3 v3.0.2 が自動変換するため許容する
    if isinstance(data, list):
        _info(
            "入力 JSON はトップレベル配列 (AlphaFold Server 形式)。AF3 が起動時に自動変換します。"
            "各エントリで modelSeeds が省略されている場合はランダムシードが生成され、"
            "dialect/version は 'alphafoldserver'/1 として扱われます。再現性が必要なら明示的に modelSeeds を設定してください。"
        )
        return

    if not isinstance(data, dict):
        _err(
            "入力 JSON はオブジェクトまたは配列である必要があります "
            "(dialect='alphafold3' または AlphaFold Server export)"
        )

    dialect = data.get("dialect")
    if dialect != "alphafold3":
        _err(
            f"dialect が 'alphafold3' ではありません: '{dialect}'. "
            f"AlphaFold Server 形式は配列のまま渡してください (自動変換されます)。"
        )

    version = data.get("version")
    if version not in (3, 4):
        _err(f"version は 3 または 4 が推奨です (現在: {version})。新規入力は 4 を使用してください。")

    if not isinstance(data.get("sequences"), list) or len(data["sequences"]) == 0:
        _err("sequences は非空の配列である必要があります。")

    seeds = data.get("modelSeeds")
    if not isinstance(seeds, list) or len(seeds) == 0:
        _err("modelSeeds は少なくとも 1 つの整数を含む配列である必要があります。")

    if not all(isinstance(s, int) for s in seeds):
        _err("modelSeeds の各要素は整数である必要があります。")

    _info(f"入力 JSON バリデーション OK: dialect={dialect}, version={version}, seeds={seeds}")


def _validate_directories(model_dir: Path, db_dir: Path, output_dir: Path, stage: str) -> None:
    """必要なディレクトリと重みファイルの存在をステージ別にチェック."""
    # 推論を実行するステージのみ af3.bin を要求する (stage=msa では不要)
    if stage in ("all", "inference"):
        if not model_dir.is_dir():
            _err(f"モデルディレクトリが存在しません: {model_dir}")
        af3_bin = model_dir / "af3.bin"
        if not af3_bin.is_file():
            _err(
                f"モデル重み {af3_bin} が見つかりません。"
                f"Google 承認メールから af3.bin をダウンロードし、{model_dir} に配置してください。"
            )
        bin_mb = af3_bin.stat().st_size / (1024 * 1024)
        if bin_mb < 500 or bin_mb > 2000:
            _info(
                f"⚠️  af3.bin サイズが想定外です ({bin_mb:.0f} MB, 期待: 約 1 GB)。"
                f"承認メールの SHA-256 と比較してください。"
            )
        _info(f"モデル重み OK: {af3_bin} ({bin_mb:.0f} MB)")

    # データパイプラインを実行するステージのみ DB を要求する (stage=inference では不要)
    if stage in ("all", "msa"):
        if not db_dir.is_dir():
            _err(f"DB ディレクトリが存在しません: {db_dir}")
        if not any(db_dir.iterdir()):
            _err(f"DB ディレクトリが空です: {db_dir}。setup-af3.sh を先に実行してください。")

    output_dir.mkdir(parents=True, exist_ok=True)
    _info(f"出力ディレクトリ: {output_dir}")


def _build_docker_cmd(args: argparse.Namespace, input_path: Path) -> list[str]:
    """docker run のコマンドライン組み立て."""
    # コンテナ内パス
    container_input = "/root/af3_input/" + input_path.name
    container_output = "/root/af3_output"
    container_model = "/root/models"
    container_db = "/root/public_databases"

    cmd = [
        "docker", "run", "--rm",
        "--volume", f"{input_path.parent}:/root/af3_input:ro",
        "--volume", f"{args.output_dir}:{container_output}",
    ]
    # stage=msa は GPU 不要 (データパイプラインのみ)
    if args.stage != "msa":
        cmd += ["--gpus", "all"]
        cmd += ["--volume", f"{args.model_dir}:{container_model}:ro"]
    # stage=inference は DB 不要 (前段の <job>_data.json が MSA を含む)
    if args.stage != "inference":
        cmd += ["--volume", f"{args.db_dir}:{container_db}:ro"]

    # JAX コンパイルキャッシュ (永続領域を推奨) — 推論ステージのみ有効
    if args.jax_cache_dir and args.stage != "msa":
        cache_path = Path(args.jax_cache_dir).expanduser()
        cache_path.mkdir(parents=True, exist_ok=True)
        cmd += ["--volume", f"{cache_path}:/root/jax-cache"]

    # unified memory (5,120 トークンを大きく超える入力用、DeepMind performance.md 準拠)
    if args.unified_memory and args.stage != "msa":
        cmd += [
            "-e", "XLA_PYTHON_CLIENT_PREALLOCATE=false",
            "-e", "TF_FORCE_UNIFIED_MEMORY=true",
            "-e", "XLA_CLIENT_MEM_FRACTION=3.2",
        ]

    cmd += [
        args.docker_image,
        "python", "run_alphafold.py",
        f"--json_path={container_input}",
        f"--output_dir={container_output}",
    ]
    if args.stage != "msa":
        cmd.append(f"--model_dir={container_model}")
    if args.stage != "inference":
        cmd.append(f"--db_dir={container_db}")

    if args.jax_cache_dir and args.stage != "msa":
        cmd.append("--jax_compilation_cache_dir=/root/jax-cache")

    # ステージ制御
    if args.stage == "msa":
        cmd.append("--run_inference=false")
    elif args.stage == "inference":
        cmd.append("--run_data_pipeline=false")
        # AF3 v3.0.2 は非空出力先に対して既定で target_<timestamp> を作成する。
        # MSA ステージが作った <job>/ に推論結果を追加するため、force_output_dir=true を指定。
        cmd.append("--force_output_dir=true")
    # stage=all はフラグ追加なし (両方実行)

    if args.flash_attention_xla:
        cmd.append("--flash_attention_implementation=xla")

    if args.extra:
        cmd += shlex.split(args.extra)

    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(
        description="AlphaFold 3 Docker wrapper for Azure ML Compute Instance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--input", required=True, type=Path,
                    help="AF3 入力 JSON (dialect=alphafold3, version=4)")
    ap.add_argument("--model-dir", required=True, type=Path,
                    help="af3.bin を含むディレクトリ (絶対パス推奨)")
    ap.add_argument("--db-dir", required=True, type=Path,
                    help="fetch_databases.sh の展開先 (/mnt/af3/public_databases)")
    ap.add_argument("--output-dir", required=True, type=Path,
                    help="推論結果を書き出す親ディレクトリ (/mnt/af3/outputs)")
    ap.add_argument("--docker-image", default="alphafold3:v3.0.2",
                    help="AF3 の Docker イメージタグ")
    ap.add_argument("--jax-cache-dir", type=str, default=None,
                    help="JAX コンパイルキャッシュ (永続領域を推奨、例: ~/cloudfiles/jax-cache)")
    ap.add_argument("--stage", choices=["all", "msa", "inference"], default="all",
                    help="実行ステージ: all=通常, msa=データパイプラインのみ, inference=推論のみ")
    ap.add_argument("--unified-memory", action="store_true",
                    help="XLA unified memory を有効化 (5,120 トークン超の場合に必要)")
    ap.add_argument("--flash-attention-xla", action="store_true",
                    help="flash_attention_implementation=xla を指定 (非 H100 互換モード、遅い)")
    ap.add_argument("--extra", default="",
                    help="run_alphafold.py への追加フラグ (shlex で分割)")
    ap.add_argument("--dry-run", action="store_true",
                    help="docker コマンドを表示するだけで実行しない")
    args = ap.parse_args()

    # 絶対パス化 (Docker volume mount で相対パスは扱いにくい)
    args.input = args.input.resolve()
    args.model_dir = args.model_dir.resolve()
    args.db_dir = args.db_dir.resolve()
    args.output_dir = args.output_dir.resolve()

    _info(f"入力: {args.input}")
    _info(f"ステージ: {args.stage}")
    _info(f"Docker image: {args.docker_image}")

    # バリデーション
    _validate_input_json(args.input)
    _validate_directories(args.model_dir, args.db_dir, args.output_dir, args.stage)

    # docker コマンド組み立て
    cmd = _build_docker_cmd(args, args.input)
    _info("docker コマンド:")
    print("  " + " ".join(shlex.quote(c) for c in cmd), flush=True)

    if args.dry_run:
        _info("--dry-run のためコマンド実行をスキップします。")
        return 0

    # 実行
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, check=False)
    except FileNotFoundError:
        _err("docker コマンドが見つかりません。setup-af3.sh を先に実行してください。")
    elapsed = time.time() - t0

    _info(f"経過時間: {elapsed:.1f} 秒")
    if proc.returncode != 0:
        _err(f"AF3 実行が終了コード {proc.returncode} で失敗しました。", code=proc.returncode)

    # 出力サマリ
    for job_name in _extract_job_names(args.input):
        job_dir = args.output_dir / job_name
        _info(f"出力ディレクトリ: {job_dir}")
        _print_summary(job_dir)
    return 0


def _extract_job_names(input_path: Path) -> list[str]:
    """入力 JSON の `name` フィールドから、AF3 の sanitised_name() 規則で正規化した
    出力ディレクトリ名の一覧を返す (トップレベル配列の場合は全ジョブ分).

    AF3 v3.0.2 の sanitised_name():
      1. lowercase
      2. スペースを '_' に置換
      3. [a-z0-9_-] 以外の文字を削除
    """
    try:
        data = json.loads(input_path.read_text())
    except Exception:
        return []
    entries: list[dict] = []
    if isinstance(data, list):
        entries = [e for e in data if isinstance(e, dict)]
    elif isinstance(data, dict):
        entries = [data]
    names: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            continue
        lowered = name.lower().replace(" ", "_")
        sanitised = re.sub(r"[^a-z0-9_-]", "", lowered)
        if sanitised:
            names.append(sanitised)
    return names


def _print_summary(job_dir: Path) -> None:
    """summary_confidences.json があれば主要指標を表示."""
    # トップランクの <job>_summary_confidences.json だけを対象にする (サンプル別 _seed-*_sample-* は除外)
    summaries = [
        p for p in job_dir.glob("*_summary_confidences.json")
        if "_seed-" not in p.name
    ]
    if not summaries:
        _info("summary_confidences.json が見つかりません (ステージが 'msa' なら正常)")
        return

    for path in summaries:
        try:
            s = json.loads(path.read_text())
        except Exception as e:
            _info(f"⚠️  {path} の読み込みに失敗: {e}")
            continue
        _info(f"--- {path.name} ---")
        for k in ("ptm", "iptm", "ranking_score", "fraction_disordered", "has_clash"):
            if k in s:
                _info(f"  {k}: {s[k]}")

    # ranking_scores.csv → <job>_ranking_scores.csv
    csv_files = list(job_dir.glob("*_ranking_scores.csv"))
    if csv_files:
        _info(f"ranking_scores.csv: {csv_files[0]}")


if __name__ == "__main__":
    # HF_HOME や CUDA 環境変数の設定不要 (Docker 内で処理されるため)
    sys.exit(main())
