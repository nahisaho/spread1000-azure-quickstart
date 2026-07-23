"""GraphRAG インデックス構築後、任意クエリを実行するラッパー。

使い方:
  python src/query.py --method global --query "Meiji 期の主要人物とその関係は?"
  python src/query.py --method local  --query "福澤諭吉の思想と教育活動は?"
"""
from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=["local", "global"], default="global")
    parser.add_argument("--query", required=True)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent / "ragtest"))
    args = parser.parse_args()

    if not Path(args.root, "output").exists():
        sys.exit(f"[error] {args.root}/output が見つかりません。先に src/run.sh を実行してください。")

    cmd = [
        sys.executable, "-m", "graphrag", "query",
        "--root", args.root,
        "--method", args.method,
        "--query", args.query,
    ]
    print(f"[cmd] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
