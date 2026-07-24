# 03 — 画像復元 U-Net（Gaussian ノイズ除去）

**対象**: 低品質画像復元、RAW ノイズ除去、磁気光学画像、超伝導線材可視化など、**劣化画像 → 高品質画像** の対応関係を学習させたい SPReAD-1000 電気工学・情報科学分野の研究者
**目標**: ノートPC の CPU だけで、**合成データ生成 → 学習 → PSNR/SSIM 評価 → 復元画像可視化** までを ≤ 20 分・完全無料で体験する
**手法**: 幾何プリミティブ (矩形・円・グラデーション) から生成した合成クリーン画像 + 加算 Gaussian ノイズ × コンパクト U-Net（117,073 パラメータ）

> [!NOTE]
> このシナリオは **ローカル CPU 完結** です。Azure リソースは不要ですが、後半のオプションで Azure ML T4 GPU にスケールする手順も紹介します。合成データを使うため、公開データセットのダウンロード・ライセンスに悩む必要がありません。

## 全体像

```
generate_data.py
   ├→ data/train/*.npz   (clean, noisy pair) × 200 枚
   ├→ data/val/*.npz     (clean, noisy pair) × 40 枚
   └→ data/test/*.npz    (clean, noisy pair) × 40 枚  ← held-out test split

train.py --device cpu
   ├→ outputs/best_model.pt        # ~117K params
   ├→ outputs/train_history.json
   ├→ outputs/loss_curve.png
   └→ outputs/comparison.png       # noisy | denoised | clean 3 枚並び

evaluate.py --device cpu
   ├→ outputs/metrics.json         # PSNR, SSIM, baseline vs restored
   └→ outputs/test_samples.png     # 8 サンプルの比較画像
```

## クイックスタート

```bash
# 1. 依存関係 (torch は CPU wheel index から先にインストール)
python -m pip install torch==2.7.1 torchvision==0.22.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt

# 2. 合成データ生成 (200 train + 40 val + 40 test, 30 秒)
python src/generate_data.py --n-train 200 --n-val 40 --n-test 40 --seed 42

# 3. 学習 (CPU 5〜10 分、val PSNR で早期停止)
python src/train.py --device cpu --epochs 20 --batch-size 16 --seed 42

# 4. 評価 (test split 40 画像で PSNR/SSIM 計算, 30 秒)
python src/evaluate.py --device cpu
```

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| クリーン画像 | 合成幾何プリミティブ (skimage.draw + scipy.ndimage) | 完全再現可能、ライセンスフリー、ダウンロード不要 |
| 劣化モデル | Gaussian 加算ノイズ (σ=0.10) | 最も基本的でよく理解された劣化タイプ |
| モデル | MiniUNet (3 レベル、117,073 params) | D-3 セグメンテーションと同じ構造を回帰に転用 |
| 損失 | L1 (MAE) | Gaussian ノイズ除去で L2 より鮮鋭度が保たれる (Zhao et al. 2017) |
| 評価 | PSNR + SSIM (torchmetrics.image) | 画像復元の標準指標、baseline (noisy 自体) と比較 |
| 学習 | PyTorch 2.7.1 (CPU) + AdamW + CosineAnnealingLR | 教材向け標準構成 |
| 可視化 | matplotlib 3.9+ | ヘッドレス保存のみ |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md) — Python、依存、想定所要時間
2. [データ生成](docs/02-generate-data.md) — 合成画像のパターンとノイズモデル
3. [学習](docs/03-train.md) — CLI、L1 損失、PSNR 早期停止、再現性
4. [結果の読み方](docs/04-understand-results.md) — PSNR/SSIM の意味、baseline との比較、比較画像
5. [Azure ML T4 で GPU 実行 (任意)](docs/05-azure-ml-t4.md) — CommandJob YAML、費用目安
6. [片付けと次のステップ](docs/06-cleanup.md) — 削除、応用のヒント (実データ、他劣化タイプ)
7. [倫理と限界](docs/07-ethics-and-limits.md) — 合成データの限界、実データ応用時の注意、hallucination 抑制

トラブル対応: [troubleshooting.md](troubleshooting.md)

## 依存関係の固定

`requirements.in` (上位依存) + `pip-compile` でハッシュ付きロックファイルを生成します:

```bash
pip install pip-tools
# CPU ローカル用
pip-compile requirements.in --generate-hashes --output-file requirements.lock
# AzureML GPU 環境用
pip-compile requirements-gpu.in --generate-hashes --output-file requirements-gpu.lock
```

生成した `requirements.lock` / `requirements-gpu.lock` をコミットすることで再現可能なインストールが保証されます。

## ライセンス

- 本シナリオのコード: リポジトリのライセンスに従う
- **データ**: 完全合成のため追加のライセンス制約なし

## 免責

**本教材のモデルは教育・研究用のノイズ除去デモです。実データ (RAW、磁気光学、医用画像等) に適用する際は、以下を必ず検証してください:**

1. 合成ノイズと実ノイズの分布差（ショットノイズ、量子化ノイズ、パターンノイズは Gaussian と異なる）
2. 復元結果に **偽構造 (hallucination)** が含まれていないか（測定値としての信頼性）
3. 医療応用の場合は SaMD 該当性の検討

詳細は [docs/07-ethics-and-limits.md](docs/07-ethics-and-limits.md) を参照してください。
