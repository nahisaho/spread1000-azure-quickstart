# 01 — 前提条件

## 想定環境

| 項目 | 推奨 | 最小 |
|---|---|---|
| OS | Windows 11 / macOS 13+ / Ubuntu 22.04+ | Python 3.10 が動く任意の OS |
| Python | **3.12.x** | 3.12.x |
| メモリ | 8 GB | 4 GB |
| 空きディスク | **500 MB** | 350 MB |
| CPU コア数 | 4 コア以上 | 2 コア |
| ネットワーク | UCI 公式リポジトリ (`archive.ics.uci.edu`) に接続可能 | 同左 |

**GPU は不要です。** すべて CPU で完結します。

## Azure リソース

このシナリオでは **Azure リソースは一切必要ありません**。無料でローカル完結します。

- 発展編として GPU 実行を試したい場合のみ、 [docs/05-azure-ml-t4.md](05-azure-ml-t4.md) で Azure ML T4 の使い方を紹介します
- その場合でも 20 分程度の実行で **約 20〜60 円** 程度に収まります

## Python 環境

システム Python を汚さないために `venv` の使用を推奨します。

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

`requirements.txt` は CPU 版 PyTorch を [公式 CPU wheel index](https://download.pytorch.org/whl/cpu) から取得します。標準の PyPI 版 torch は Linux で CUDA ランタイムを含み無用に大きくなるため、明示的に CPU 版を指定しています。

## 想定所要時間

| ステップ | 目安 (CPU, 4 コア) |
|---|---:|
| 依存インストール | 1〜2 分 |
| `prepare_data.py` (DL + 展開 + NPZ 化) | 1〜2 分 (回線速度依存) |
| `train.py` (15 epoch, batch=128) | 5〜10 分 |
| `evaluate.py` | < 1 分 |
| **合計** | **8〜15 分** |

回線が遅い環境では ZIP DL が支配的になりますが、キャッシュされるため 2 回目以降はスキップされます。

## トラブル時

問題が起きたら [`troubleshooting.md`](../troubleshooting.md) を参照してください。よくある症状の解決策をまとめています。
