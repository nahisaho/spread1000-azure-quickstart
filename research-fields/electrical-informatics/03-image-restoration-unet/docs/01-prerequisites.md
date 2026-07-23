# 01 — 前提条件

## 想定環境

| 項目 | 推奨 | 最小 |
|---|---|---|
| OS | Windows 11 / macOS 13+ / Ubuntu 22.04+ | Python 3.11 が動く任意の OS |
| Python | **3.12.x** | 3.11.x |
| メモリ | 8 GB | 4 GB |
| 空きディスク | 200 MB | 150 MB |
| CPU コア数 | 4 コア以上 | 2 コア |

**GPU は不要です**。すべて CPU で完結します。

## Azure リソース

このシナリオでは **Azure リソースは一切必要ありません**。無料でローカル完結します。

- 発展編として GPU 実行を試したい場合のみ、 [docs/05-azure-ml-t4.md](05-azure-ml-t4.md) を参照

## Python 環境

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

依存インストール（**torch は先に CPU wheel index から**）:

```bash
python -m pip install --upgrade pip
python -m pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

`torch` を先にインストールする理由は、`--index-url` を全体に効かせると他のパッケージ (numpy, scipy 等) が PyPI から取得できなくなるためです。分けて実行してください。

## 想定所要時間

| ステップ | 目安 (CPU, 4 コア) |
|---|---:|
| 依存インストール | 2〜3 分 |
| `generate_data.py` (240 サンプル) | 30 秒 |
| `train.py` (20 epoch, batch=16) | 5〜10 分 |
| `evaluate.py` | 30 秒 |
| **合計** | **8〜14 分** |

## トラブル時

[`troubleshooting.md`](../troubleshooting.md) を参照してください。
