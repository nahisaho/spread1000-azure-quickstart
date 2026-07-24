# 01 — 前提条件

## 想定環境

| 項目 | 推奨 | 最小 |
|---|---|---|
| OS | Windows 11 / macOS 13+ / Ubuntu 22.04+ | Python 3.12.x が動く任意の OS |
| Python | **3.12.x** | 3.12.x |
| メモリ | 8 GB | 4 GB |
| 空きディスク | **500 MB** | 350 MB |
| CPU コア数 | 4 コア以上 | 2 コア |
| ネットワーク | UCI 公式リポジトリ (`archive.ics.uci.edu`) に接続可能 | 同左 |

**GPU は不要です。** すべて CPU で完結します。

## Azure リソース

このシナリオでは **Azure リソースは一切必要ありません**。無料でローカル完結します。

- 発展編として GPU 実行を試したい場合のみ、[docs/05-azure-ml-t4.md](05-azure-ml-t4.md) を参照してください
- その場合でも短時間の実行に限定すれば小額です

## Python 環境

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

依存インストール:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
