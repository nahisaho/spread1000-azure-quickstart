# 03 — 顕微鏡画像セグメンテーション (合成 SEM 相当画像 + MONAI U-Net)

Voronoi 多角形で生成した合成の多結晶 SEM 相当画像で **粒界セグメンテーション** を学習する、
**MONAI U-Net** (~117K パラメータ) のクイックスタートです。

> **⚡ 最短パス（推奨）**: **CPU / WSL2 / ローカル Python で完結、Azure 課金 0 円。**
> 128×128 の合成データ 200 枚を 10 エポック学習して 2 分弱で結果が出ます。
>
> 256×256 や実データにスケールしたい場合は Azure ML GPU (T4) を利用 ([docs/03-aml-gpu.md](docs/03-aml-gpu.md)、$0.35 未満)。

## 再現性・依存パッケージのインストール方法

完全再現可能なインストールには pip-tools のハッシュロックファイルを推奨します:

```bash
pip install pip-tools
pip-compile --generate-hashes \
  --output-file=requirements.lock requirements.in
pip install --require-hashes -r requirements.lock
```

開発環境での簡易インストール:

```bash
# 1. PyTorch を先にインストール (CPU wheel)
pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu

# 2. MONAI + その他依存パッケージ
pip install -r requirements.txt
```

## SPReAD-1000 対応課題

材料・応用医工学分野で **SEM/TEM/光学顕微鏡** の画像解析を扱う課題（粒界検出、粒子計数、欠陥ローカリゼーション など）向け。

## 使う技術

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| **MONAI 1.4.0** | U-Net / DiceCELoss / DiceMetric / CacheDataset / transforms | **Apache 2.0** |
| PyTorch **2.7.x** + torchvision 0.22.x | 学習バックエンド | BSD |
| scikit-image `>=0.24` | Voronoi 分割・境界抽出 | Modified BSD |
| SciPy `>=1.13` | `scipy.spatial.cKDTree` | BSD-3 |
| torchmetrics `>=1.4` | IoU (Jaccard) | Apache 2.0 |
| matplotlib | モンタージュ出力 | PSF |

**パラメータ数の確認 (プログラム的生成)**:
```bash
python -c "import sys; sys.path.insert(0,'src'); \
  from model import build_model, count_parameters; \
  print(count_parameters(build_model()))"
# → 実際の値を確認してください
```

**引用**: Ronneberger et al., *U-Net*, MICCAI 2015. arXiv:1505.04597.

## クイックスタート (CPU / ローカル)

```bash
# 1. Python 3.10〜3.12 の仮想環境
python3.12 -m venv .venv
source .venv/bin/activate

# 2. PyTorch を先にインストール (CPU wheel)
pip install --upgrade pip
pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu

# 3. MONAI + その他の依存
pip install -r requirements.txt

# 4. 合成データを目視確認したい場合（任意）
python src/generate_data.py --task grains --n 4 --output data/samples/

# 5. 学習 & 検証（CPU 10 エポック、~2 分）
python src/train.py --task grains --image-size 128 \
  --n-train 200 --n-val 50 --epochs 10 --device cpu --output data/

# 6. テストセット評価（任意）
python src/evaluate.py \
  --checkpoint data/checkpoints/best_model.pth \
  --task grains --image-size 128 --output data/

# 7. チェックポイント検証（デプロイ前）
python src/verify.py \
  --checkpoint data/checkpoints/best_model.pth \
  --test-metrics data/predictions/test_metrics.json \
  --min-dice 0.60
```

**出力**:
- `data/metrics.json` — train/val loss、IoU、Dice 履歴、再現性メタデータ、チェックポイント SHA-256
- `data/predictions/montage_epoch010.png` — 入力 | 正解 | 予測 のパネル画像
- `data/predictions/per_image_metrics.json` — 検証画像ごとの IoU/Dice
- `data/predictions/test_metrics.json` — テストセット集計指標
- `data/checkpoints/best_model.pth` — ベストエポックの重み

**成功基準 (Voronoi 粒界、10 epochs)**:
- 検証 IoU 0.55〜0.75 (粒界は 1〜2 ピクセル幅で本質的に低め)
- 検証 Dice 0.70〜0.85
- 学習損失が単調に減少

## タスクの選択

| タスク | 内容 | 対応する実タスク |
|---|---|---|
| `grains` (既定) | Voronoi 多角形の粒界マップ | SEM 多結晶粒界、EBSD 位相境界 |
| `particles` | ランダム円のセグメンテーション | TEM ナノ粒子、SEM 析出物 |

## ディレクトリ構成

```
03-microscopy-segmentation/
├── README.md
├── troubleshooting.md
├── requirements.in            # top-level constraints (pip-compile input)
├── requirements.txt           # simplified install (no hashes)
├── azureml/
│   ├── train_job.yml          # AML CommandJob — training
│   └── evaluate_job.yml       # AML CommandJob — evaluation
├── infra/
│   ├── main.bicep             # AML workspace + Storage + KV + ACR + LA
│   ├── parameters.example.json
│   ├── deploy.sh              # end-to-end deploy script
│   └── environments/gpu/
│       ├── Dockerfile         # MCR GPU base + hash-pinned deps
│       ├── environment.yml    # AML environment definition
│       └── requirements-gpu.in
├── src/
│   ├── generate_data.py       # Voronoi & 粒子生成 (preview/splits mode)
│   ├── model.py               # MONAI UNet wrapper
│   ├── train.py               # 学習 + 検証 + モンタージュ保存
│   ├── evaluate.py            # テストセット評価
│   └── verify.py              # チェックポイント検証
├── data/                      # 実行時生成 (gitignore)
└── docs/
    ├── 01-prerequisites.md
    ├── 02-cpu-quickstart.md
    ├── 03-aml-gpu.md
    ├── 04-run-training.md
    ├── 05-understand-results.md
    ├── 06-cleanup.md
    └── 07-ethics-and-limits.md
```

## Azure インフラ のセットアップ

```bash
export RG="rg-microseg-dev"
export LOC="japaneast"
export NAME_PREFIX="microseg"
bash infra/deploy.sh
source .env  # ← 生成された .env を読み込む
```

## コスト目安

| 実行環境 | 128×128 x 200 枚 x 10 epochs | コスト |
|---|---:|---:|
| **ローカル / WSL2 (CPU 4 コア)** | 1〜3 分 | **$0** |
| Azure ML CI (`NC4as_T4_v3`, PAYG) | 5 分 (256×256 x 500 枚 x 20 epochs) | ~$0.35 |
| Azure ML Cluster (low_priority) | 同上 | ~$0.11 |

## 参考文献

- Ronneberger et al., *U-Net*, MICCAI 2015. arXiv:1505.04597
- MONAI Consortium, *Project MONAI*, GitHub. https://github.com/Project-MONAI/MONAI
- van der Walt et al., *scikit-image*, PeerJ 2:e453 (2014)
- 詳細な引用と限界は [docs/07-ethics-and-limits.md](docs/07-ethics-and-limits.md)
