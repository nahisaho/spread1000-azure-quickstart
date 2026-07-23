# 01 — 前提条件と環境準備

## 対象読者

- Python プログラミングの基礎（`pip install`、venv、for ループ、numpy 配列）
- 畳み込みニューラルネットの概要は既知（U-Net、BCE Loss、IoU/Dice の意味がわかる）
- Azure は初めて（ローカル/WSL2 で完結できるので Azure 未使用でも OK）

## 必須ソフトウェア

| ソフト | バージョン | 備考 |
|---|---|---|
| **Python** | **3.10 / 3.11 / 3.12** | 3.13 も動くが D-1/D-2 と揃えて 3.12 推奨 |
| **PyTorch** | **2.7.1** | torchvision 0.22.1 と組で |
| pip | 24.x 以降 | |
| Git | 任意 | 本リポジトリを clone する場合 |

## OS 別の推奨環境

| OS | 推奨実行環境 |
|---|---|
| **Windows** | **WSL2 + Ubuntu 22.04** |
| macOS (M1/M2/M3) | ネイティブ Python 3.12 (`brew install python@3.12`) |
| Linux | ネイティブ Python 3.10〜3.12 |

## インストール手順

### 1. Python 3.12 の仮想環境を作成

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -V   # Python 3.12.x を確認
```

### 2. PyTorch を先に固定インストール

**CPU 版**:
```bash
pip install --upgrade pip
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
```

**CUDA 12.1 版 (NVIDIA GPU あり)**:
```bash
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu126
```

**GPU 動作確認**:
```python
import torch
print(torch.cuda.is_available())   # True で GPU 使用可
print(torch.cuda.get_device_name(0))
```

### 3. その他の依存

```bash
pip install -r requirements.txt
```

- `scikit-image>=0.24` — Voronoi 分割 + 境界抽出 + 描画
- `scipy>=1.13` — `scipy.spatial.Voronoi`
- `numpy>=1.26`
- `matplotlib>=3.9` — モンタージュ画像出力
- `torchmetrics>=1.4` — IoU (Jaccard)、F1 (Dice)

### 4. 動作確認

```bash
# 合成データを 4 枚だけ生成 (data/samples/ に PNG が出る)
python src/generate_data.py --task grains --n 4 --output data/samples/
ls data/samples/
```

`grains_00.png` などが 4 枚できれば準備完了です。

## 既知の落とし穴

| 症状 | 原因 | 対処 |
|---|---|---|
| `RuntimeError: found dtype Byte` in loss | mask が `bool`/`uint8` | Dataset で `torch.from_numpy(m).float()` に |
| Val loss が下がるが IoU が 0 | Sigmoid の二重適用 | model.forward は logits のみ返す (本実装済み) |
| WSL2 で DataLoader が hang | `num_workers>0` で spawn 失敗 | `--num-workers 0` (既定) を維持 |
| IoU が 0.15 でとまる | エポック不足 or 学習率不適 | `--epochs 20 --lr 5e-4` を試す |

より詳しくは [../troubleshooting.md](../troubleshooting.md) を参照。

## Azure ML で実行する場合

大規模化 (256×256 x 500 枚 x 20 epochs 以上) が必要な場合のみ [03-aml-gpu.md](03-aml-gpu.md) を参照。**それ以外はローカル CPU で十分**です。
