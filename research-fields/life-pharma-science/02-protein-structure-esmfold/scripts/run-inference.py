#!/usr/bin/env python3
"""
ESMFold 推論 CLI — Azure ML Compute Instance 用

Meta AI の facebook/esmfold_v1 を用いて、FASTA ファイルからタンパク質 3D 構造を予測。
出力: PDB ファイル (per-sequence) + pLDDT CSV + サマリ CSV

使い方:
    python run-inference.py \\
        --input my.fasta \\
        --output ./output/ \\
        --half-precision \\
        --chunk-size 64

必要環境: setup-esmfold.sh で構築した conda env 'esmfold'
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Iterable

# HF_HOME を setup-esmfold.sh の設定に合わせる (import 前に必要)
_HF_CACHE = Path.home() / "cloudfiles" / "hf_cache"
if _HF_CACHE.exists():
    os.environ.setdefault("HF_HOME", str(_HF_CACHE))

import torch  # noqa: E402
from Bio import SeqIO  # noqa: E402
from transformers import AutoTokenizer, EsmForProteinFolding  # noqa: E402

# ESMFold の位置埋め込み上限 (これを超えると外挿になり品質が急落)
MAX_SUPPORTED_LENGTH = 1024
# HuggingFace facebook/esmfold_v1 のトークナイザは標準 20 アミノ酸 + X のみを扱う。
# B/Z/J/U/O 等の曖昧・希少コードはトークナイズ段階でエラーになる:
#   - B = Asn/Asp 曖昧, Z = Glu/Gln 曖昧, J = Ile/Leu 曖昧 (拡張 IUPAC)
#   - U = Selenocysteine, O = Pyrrolysine (稀な 21/22 番目のアミノ酸)
# → 本ラッパーはこれらを reject する。X への正規化が必要な場合は
#   --coerce-nonstandard-to-x フラグを明示的に指定させる。
_VALID_AA = set("ACDEFGHIKLMNPQRSTVWY")
_X_TOKEN = {"X"}
_NON_TOKENIZABLE = set("BZJUO")


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _validate_sequence(
    seq_id: str, seq: str, max_length: int, coerce_nonstandard_to_x: bool = False,
) -> tuple[bool, str]:
    """Return (ok, cleaned_seq_or_reason).

    - Rejects sequences containing internal stops '*' or gaps '-' (silently stripping
      would materially alter the predicted protein). Trailing '*' as an explicit stop
      symbol is tolerated by trimming.
    - Rejects B/Z/J/U/O unless --coerce-nonstandard-to-x is set; the ESMFold tokenizer
      does not accept them.
    """
    raw = seq.upper()
    # Allow only a trailing single '*' (translation stop convention); reject internal '*' / '-'
    stripped = raw.rstrip("*")
    if "*" in stripped or "-" in stripped:
        return False, "internal '*' or '-' found (would silently change sequence)"
    s = stripped
    if not s:
        return False, "empty sequence"
    if len(s) > max_length:
        return False, f"length {len(s)} > max_length {max_length}"
    non_tokenizable = set(s) & _NON_TOKENIZABLE
    if non_tokenizable:
        if not coerce_nonstandard_to_x:
            return False, (
                f"contains ESMFold-non-tokenizable residues {sorted(non_tokenizable)}. "
                "Re-run with --coerce-nonstandard-to-x to normalize these to X (predicted structure "
                "will not reflect the exact residue identity)."
            )
        s = "".join(c if c not in _NON_TOKENIZABLE else "X" for c in s)
        _log(f"⚠  {seq_id}: 非標準残基 {sorted(non_tokenizable)} を 'X' に正規化しました (精度低下の可能性)")
    unknown = set(s) - _VALID_AA - _X_TOKEN
    if unknown:
        return False, f"contains non-standard chars: {sorted(unknown)}"
    if "X" in set(s):
        _log(f"⚠  {seq_id}: 'X' (未知残基) を含みます (該当位置の側鎖予測は信頼できません)")
    return True, s


def _load_fasta(path: Path) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    with path.open() as fh:
        for rec in SeqIO.parse(fh, "fasta"):
            records.append((rec.id, str(rec.seq)))
    if not records:
        raise ValueError(f"No sequences found in {path}")
    return records


def _load_model(chunk_size: int | None, half_precision: bool) -> tuple[EsmForProteinFolding, "AutoTokenizer"]:
    _log("Loading facebook/esmfold_v1 (初回は 30-60 秒かかります)...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
    model = EsmForProteinFolding.from_pretrained(
        "facebook/esmfold_v1",
        low_cpu_mem_usage=True,
    )
    model = model.cuda().eval()
    if half_precision:
        model.esm = model.esm.half()
        _log("  → ESM stem を FP16 化しました")
    if chunk_size:
        model.trunk.set_chunk_size(chunk_size)
        _log(f"  → chunk_size = {chunk_size}")
    _log(f"Model loaded in {time.time() - t0:.1f}s")
    return model, tokenizer


def _infer_one(
    model: EsmForProteinFolding,
    tokenizer: "AutoTokenizer",
    seq_id: str,
    seq: str,
) -> tuple[str, list[float], float, float]:
    """Return (pdb_string, per_residue_plddt (0-100 scale), mean_plddt, ptm)."""
    tokens = tokenizer(
        seq, return_tensors="pt", add_special_tokens=False
    )
    tokens = {k: v.cuda() for k, v in tokens.items()}

    with torch.no_grad():
        out = model(**tokens)

    # pLDDT の値域を正規化: transformers のバージョンによって 0-1 で返るものと
    # 0-100 で返るものがある。生 tensor の最大値が 1.5 以下なら 0-1 スケールと判定し ×100。
    # PDB の B-factor 列と CSV の両方に一貫した 0-100 スケールを出力するため、
    # output_to_pdb() 前に out["plddt"] 自体を書き換える。
    plddt_all = out["plddt"]
    if float(plddt_all.max().detach().cpu()) <= 1.5:
        out["plddt"] = plddt_all * 100.0

    pdb_str = model.output_to_pdb(out)[0]

    # per-residue: index 1 は Cα atom
    plddt_tensor = out["plddt"][0, : len(seq), 1].cpu().float().numpy()
    plddt = plddt_tensor.tolist()
    mean_plddt = float(plddt_tensor.mean())

    # pTM は ModelOutput 属性経由でアクセス (キー存在は保証されない)
    ptm_val = getattr(out, "ptm", None)
    if ptm_val is None:
        ptm = float("nan")
    else:
        try:
            ptm = float(ptm_val.detach().cpu().item())
        except Exception:  # noqa: BLE001
            ptm = float("nan")

    # メモリ断片化対策 (次のシーケンスに備えて)
    torch.cuda.empty_cache()

    return pdb_str, plddt, mean_plddt, ptm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run ESMFold inference on FASTA input.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", "-i", required=True, type=Path, help="Input FASTA path")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Output directory")
    parser.add_argument(
        "--chunk-size", type=int, default=64,
        help="ESMFold trunk chunk size (小さいほど VRAM 節約・低速)",
    )
    parser.add_argument(
        "--half-precision", action="store_true",
        help="ESM stem を FP16 化 (T4 では必須)",
    )
    parser.add_argument(
        "--max-length", type=int, default=MAX_SUPPORTED_LENGTH,
        help=f"許容する最大配列長 (絶対上限 {MAX_SUPPORTED_LENGTH})",
    )
    parser.add_argument(
        "--sort-by-length", action="store_true",
        help="配列長でソートしてから処理 (GPU メモリ効率)",
    )
    parser.add_argument(
        "--summary", type=Path, default=None,
        help="サマリ CSV の出力パス (省略時: <output>/summary.csv)",
    )
    parser.add_argument(
        "--coerce-nonstandard-to-x", action="store_true",
        help="B/Z/J/U/O 等の非標準残基を 'X' に強制正規化 (既定: reject)。"
             "予測構造は該当位置の残基同一性を反映しません。",
    )
    parser.add_argument(
        "--allow-partial-success", action="store_true",
        help="1 件でも成功があれば exit 0 を返す (既定: 全件成功で 0、1 件でも失敗/skip があれば 6)。",
    )

    args = parser.parse_args(argv)
    if args.max_length > MAX_SUPPORTED_LENGTH:
        _log(f"⚠  --max-length {args.max_length} > {MAX_SUPPORTED_LENGTH} は無視して {MAX_SUPPORTED_LENGTH} を使用")
        args.max_length = MAX_SUPPORTED_LENGTH

    if not args.input.is_file():
        print(f"❌ Input not found: {args.input}", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    summary_path = args.summary or (args.output / "summary.csv")

    if not torch.cuda.is_available():
        print("❌ CUDA が使えません。GPU 付き Compute Instance を確認してください。", file=sys.stderr)
        return 3

    records = _load_fasta(args.input)
    _log(f"Loaded {len(records)} sequence(s) from {args.input}")

    validated: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    for seq_id, seq in records:
        ok, result = _validate_sequence(
            seq_id, seq, args.max_length,
            coerce_nonstandard_to_x=args.coerce_nonstandard_to_x,
        )
        if ok:
            validated.append((seq_id, result))
        else:
            _log(f"⚠  skip {seq_id}: {result}")
            skipped.append((seq_id, result))

    if not validated:
        print("❌ 有効な配列がありません", file=sys.stderr)
        return 4

    if args.sort_by_length:
        validated.sort(key=lambda x: len(x[1]))
        _log("Sorted sequences by length ascending")

    model, tokenizer = _load_model(args.chunk_size, args.half_precision)

    used_names: set[str] = set()
    n_ok = 0
    n_oom = 0
    n_err = 0

    def _safe_unique_name(seq_id: str) -> str:
        base = "".join(c if c.isalnum() or c in "-_." else "_" for c in seq_id)[:80]
        if base and base not in used_names:
            used_names.add(base)
            return base
        # 衝突または空: 決定論的なサフィックスを付与し、それでも衝突する場合は連番を追加
        import hashlib
        digest = hashlib.md5(seq_id.encode("utf-8")).hexdigest()[:8]
        prefix = base or "seq"
        candidate = f"{prefix}_{digest}"
        n = 2
        while candidate in used_names:
            candidate = f"{prefix}_{digest}_{n}"
            n += 1
        used_names.add(candidate)
        return candidate

    with summary_path.open("w", newline="") as sumfh:
        writer = csv.writer(sumfh)
        writer.writerow(["seq_id", "length", "mean_plddt", "ptm", "inference_sec", "status"])

        # 入力に含まれていた全レコードをサマリに残す (skip も含む)
        for skipped_id, reason in skipped:
            writer.writerow([skipped_id, "", "", "", "", f"skipped: {reason}"])

        for seq_id, seq in validated:
            _log(f"→ {seq_id} ({len(seq)} aa) ...")
            t0 = time.time()
            try:
                pdb_str, plddt, mean_plddt, ptm = _infer_one(model, tokenizer, seq_id, seq)
            except torch.cuda.OutOfMemoryError as exc:
                _log(f"✗ {seq_id}: CUDA OOM ({exc}). --chunk-size を下げるか GPU を上位に変更してください")
                writer.writerow([seq_id, len(seq), "", "", "", "OOM"])
                n_oom += 1
                torch.cuda.empty_cache()
                continue
            except Exception as exc:  # noqa: BLE001
                _log(f"✗ {seq_id}: 推論失敗 ({type(exc).__name__}: {exc})")
                writer.writerow([seq_id, len(seq), "", "", "", f"error: {type(exc).__name__}"])
                n_err += 1
                continue
            elapsed = time.time() - t0

            safe_id = _safe_unique_name(seq_id)
            pdb_path = args.output / f"{safe_id}.pdb"
            csv_path = args.output / f"{safe_id}_plddt.csv"

            pdb_path.write_text(pdb_str)
            with csv_path.open("w", newline="") as cfh:
                cwriter = csv.writer(cfh)
                cwriter.writerow(["residue_index", "residue", "plddt"])
                for idx, (aa, sc) in enumerate(zip(seq, plddt), start=1):
                    cwriter.writerow([idx, aa, f"{sc:.2f}"])

            _log(
                f"  ✓ {seq_id}: mean pLDDT={mean_plddt:.2f}, pTM={ptm:.3f}, {elapsed:.1f}s"
                f" → {pdb_path.name}"
            )
            writer.writerow([seq_id, len(seq), f"{mean_plddt:.2f}", f"{ptm:.3f}", f"{elapsed:.1f}", "ok"])
            n_ok += 1

    _log(f"Summary written: {summary_path}")
    _log(f"Done. {n_ok} succeeded, {n_oom} OOM, {n_err} errored, {len(skipped)} skipped.")
    # 既定は 「全件成功で 0、1 件でも失敗/skip があれば 6」。--allow-partial-success 指定時は
    # 従来通り 1 件でも成功があれば 0 を返す。
    partial_failures = n_oom + n_err + len(skipped)
    if n_ok == 0:
        return 5
    if partial_failures > 0 and not args.allow_partial_success:
        _log(f"⚠  {partial_failures} 件の失敗/skip があるため exit 6 で終了 "
             "(--allow-partial-success で 0 を返せます)")
        return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())
