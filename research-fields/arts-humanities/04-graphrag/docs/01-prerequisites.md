# 01 — 前提条件

## 環境

- Python 3.10-3.12 (graphrag 2.4 は 3.13 未サポート)
- OS: **Linux / WSL2 / macOS 推奨** (Bash と POSIX ユーティリティに依存)。Windows ネイティブ (PowerShell) からは `src/run.sh` は動きません — WSL2 か Git Bash 経由で実行してください。
- インターネット (Azure OpenAI 呼び出し)

## Azure サブスクリプション

- Azure OpenAI Service 利用申請済み
- 対象リージョン: japaneast, eastus, swedencentral 等 (gpt-4o-mini + text-embedding-3-small が同時利用可能)

## 概念

以下の用語を先に読んでおくと理解しやすいです:
- **RAG (Retrieval-Augmented Generation)** — chunk 検索 + LLM
- **ナレッジグラフ (KG)** — エンティティ (node) と関係 (edge)
- **Leiden クラスタリング** — グラフのコミュニティ検出

## Python セットアップ

```bash
cd research-fields/arts-humanities/04-graphrag
python -m venv .venv
source .venv/bin/activate   # WSL/macOS/Linux. Windows は WSL2 か Git Bash を使用してください。
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 費用の心構え

初回 index 構築は **数百回の LLM 呼び出し**が発生します。gpt-4o-mini でも本教材の 3 文書 (~5000 word) で $0.30〜$0.50、大規模文書では $10〜$100+ になり得ます。

**必ず** `.env` の `GRAPHRAG_LLM_MODEL` を `gpt-4o-mini` に設定してください (最も安価)。試行段階で `gpt-4o` にすると 10-20 倍のコストになります。
