# 03 — 顕微鏡画像セグメンテーション (合成 SEM 相当画像 + U-Net)

Voronoi 多角形で生成した合成の多結晶 SEM 相当画像で **粒界セグメンテーション** を学習する、小型 U-Net (~117K パラメータ) のクイックスタートです。

> **⚡ 最短パス（推奨）**: **CPU / WSL2 / ローカル Python で完結、Azure 課金 0 円。**128×128 の合成データ 200 枚を 10 エポック学習して 2 分弱で結果が出ます。
>
> 256×256 や実データにスケールしたい場合は Azure ML GPU (T4) を利用（[docs/03-aml-gpu.md](docs/03-aml-gpu.md)、$0.35 未満）。

## SPReAD-1000 対応課題

材料・応用医工学分野で **SEM/TEM/光学顕微鏡** の画像解析を扱う課題（粒界検出、粒子計数、欠陥ローカリゼーション など）向け。同じパイプラインで、独自の画像とマスクを渡す実データ学習へ拡張できます。

## 使う技術

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| PyTorch **2.7.x** + torchvision 0.22.x | 学習フレームワーク | BSD |
| scikit-image `>=0.24` | Voronoi 分割・境界抽出・描画 | Modified BSD |
| SciPy `>=1.13` | `scipy.spatial.Voronoi` | BSD-3 |
| torchmetrics `>=1.4` | IoU (Jaccard) / F1 (Dice) 計算 | Apache 2.0 |
| matplotlib | モンタージュ出力 | PSF |

**引用**: Ronneberger et al., *U-Net: Convolutional Networks for Biomedical Image Segmentation*, MICCAI 2015. arXiv:1505.04597.

## クイックスタート (CPU / ローカル)

```bash
# 1. Python 3.10〜3.12 の仮想環境
python3.12 -m venv .venv
source .venv/bin/activate

# 2. PyTorch を先にインストール (CPU wheel)
pip install --upgrade pip
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu

# 3. その他の依存
pip install -r requirements.txt

# 4. 合成データを目視確認したい場合（任意）
python src/generate_data.py --task grains --n 4 --output data/samples/

# 5. 学習 & 評価（CPU 10 エポック、~2 分）
python src/train.py --task grains --image-size 128 \
  --n-train 200 --n-val 50 --epochs 10 --device cpu --output data/
```

**出力**:
- `data/metrics.json` — train/val loss、IoU、Dice の履歴
- `data/predictions/montage_epoch010.png` — 入力 | 正解 | 予測 のパネル画像
- `data/predictions/per_image_metrics.json` — 検証画像ごとの IoU/Dice
- `data/checkpoints/best_model.pth` — ベストエポックの重み

**成功基準 (Voronoi 粒界、10 epochs)**:
- 検証 IoU 0.55〜0.75（粒界は 1〜2 ピクセル幅で本質的に低め）
- 検証 Dice 0.70〜0.85
- 学習損失が単調に減少している

## タスクの選択

`--task` オプションで 2 種類の合成データを切り替えられます:

| タスク | 内容 | 対応する実タスク |
|---|---|---|
| `grains` (既定) | Voronoi 多角形の粒界マップ | SEM 多結晶粒界、EBSD 位相境界 |
| `particles` | ランダム円のセグメンテーション | TEM ナノ粒子、SEM 析出物 |

## ディレクトリ構成

```
03-microscopy-segmentation/
├── README.md
├── troubleshooting.md
├── requirements.txt
├── src/
│   ├── generate_data.py   # Voronoi & 粒子生成器
│   ├── model.py           # MiniUNet (3 レベル, ~117K params)
│   └── train.py           # 学習 + 検証 + モンタージュ保存
├── data/                  # 実行時生成 (gitignore)
└── docs/
    ├── 01-prerequisites.md
    ├── 02-cpu-quickstart.md
    ├── 03-aml-gpu.md
    ├── 04-run-training.md
    ├── 05-understand-results.md
    ├── 06-cleanup.md
    └── 07-ethics-and-limits.md
```

## コスト目安

| 実行環境 | 128×128 x 200 枚 x 10 epochs | コスト |
|---|---:|---:|
| **ローカル / WSL2 (CPU 4 コア)** | 1〜3 分 | **$0** |
| Azure ML CI (`NC4as_T4_v3`, PAYG) | 5 分（256×256 x 500 枚 x 20 epochs） | ~$0.35 |

## 参考文献

- Ronneberger et al., *U-Net: Convolutional Networks for Biomedical Image Segmentation*, MICCAI 2015. arXiv:1505.04597
- van der Walt et al., *scikit-image: image processing in Python*, PeerJ 2:e453 (2014). DOI:10.7717/peerj.453
- 詳細な引用と限界は [docs/07-ethics-and-limits.md](docs/07-ethics-and-limits.md)
