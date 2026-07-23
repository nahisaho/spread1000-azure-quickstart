"""GraphRAG インデックス構築後、任意クエリを実行するラッパー。

使い方:
  python src/query.py --method global --query "Meiji 期の主要人物とその関係は?"
  python src/query.py --method local  --query "福澤諭吉の思想と教育活動は?"

前提: プロジェクトルートの `.env` に GRAPHRAG_* 変数が定義されていること。
`src/run.sh` を先に実行済みで `ragtest/output/` が存在すること。
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["local", "global", "drift"], default="global")
    parser.add_argument("--query", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent / "ragtest"))
    args = parser.parse_args()

    # プロジェクトルート .env を読み込む (settings.yaml の ${GRAPHRAG_*} 展開に必要)
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if not env_path.exists():
        sys.exit(f"[error] {env_path} が見つかりません。cp .env.example .env で作成して編集してください。")
    load_dotenv(env_path)
    for v in ("GRAPHRAG_API_KEY", "GRAPHRAG_API_BASE", "GRAPHRAG_API_VERSION",
              "GRAPHRAG_LLM_DEPLOYMENT_NAME", "GRAPHRAG_EMBEDDING_DEPLOYMENT_NAME"):
        if not os.environ.get(v):
            sys.exit(f"[error] {v} が .env に定義されていません")

    if not Path(args.root, "output").exists():
        sys.exit(f"[error] {args.root}/output が見つかりません。先に bash src/run.sh を実行してください。")

    cmd = [
        sys.executable, "-m", "graphrag", "query",
        "--root", args.root,
        "--method", args.method,
        "--query", args.query,
    ]
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True, env=os.environ.copy())


if __name__ == "__main__":
    main()
