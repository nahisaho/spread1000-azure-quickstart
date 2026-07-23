# 02 — 時系列生体信号分類（1D-CNN, UCI HAR）

**対象**: EMG・EEG・IMU・超音波・モーションキャプチャなど、**多チャネル時系列** から離散クラスを識別したい SPReAD-1000 電気工学・情報科学分野の研究者
**目標**: ノートPC の CPU だけで、**ダウンロード → 学習 → 評価 → 混同行列・分類レポート保存** までを ≤ 20 分・完全無料で体験する
**手法**: UCI HAR（30 名の被験者、6 活動、9 チャネル × 128 時点） × コンパクト 1D-CNN（約 32K パラメータ）

> [!NOTE]
> このシナリオは **ローカル CPU 完結** です。Azure リソースは不要ですが、後半のオプションで Azure ML T4 GPU にスケールする手順も紹介します。

## 全体像

```
UCI HAR ZIP (58 MB)
   ↓ prepare_data.py
data/har_windows.npz        # (N, 9, 128) float32, subject_id, label
   ↓ train.py --device cpu
outputs/best_model.pt       # ~32K params
outputs/normalization.npz   # per-channel mean/std (train fold only)
   ↓ evaluate.py
outputs/metrics.json
outputs/classification_report.json
outputs/confusion_matrix.png
outputs/loss_curve.png
```

## クイックスタート

```bash
# 1. 依存関係
python -m pip install -r requirements.txt

# 2. データ準備 (58 MB DL + 展開 + NPZ 化, 2 分程度)
python src/prepare_data.py

# 3. 学習 (CPU 5〜10 分、被験者独立 val で早期停止)
python src/train.py --device cpu --epochs 15 --batch-size 128 --seed 42

# 4. 評価 (公式 test 2947 窓, 30 秒)
python src/evaluate.py
```

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| データセット | UCI HAR (CC BY 4.0) | セグメント済み、被験者独立公式分割、非臨床 |
| 前処理 | numpy + urllib.request + zipfile | 標準ライブラリのみ、追加依存なし |
| モデル | 3 ブロック Conv1d-BN-ReLU-Pool + GAP + Linear | ~32K params, CPU で数分 |
| 学習 | PyTorch 2.13.0 (CPU) + AdamW + CosineAnnealingLR | 標準構成、教材向け |
| 評価 | scikit-learn 1.9.0 (classification_report / confusion_matrix) | 業界標準 |
| 可視化 | matplotlib 3.11.1 | 保存のみ (GUI 不要) |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md) — Python 3.12、pip、ディスク容量、想定所要時間
2. [データ準備](docs/02-prepare-data.md) — UCI HAR の構造と `prepare_data.py` の動作
3. [学習](docs/03-train.md) — CLI オプション、被験者独立分割、標準化、再現性
4. [結果の読み方](docs/04-understand-results.md) — accuracy vs macro-F1、混同行列の見方
5. [Azure ML T4 で GPU 実行 (任意)](docs/05-azure-ml-t4.md) — CommandJob YAML、費用目安、環境選定
6. [片付けと次のステップ](docs/06-cleanup.md) — Azure 資産の削除、応用のヒント
7. [倫理と限界](docs/07-ethics-and-limits.md) — 医療機器ではない、被験者独立汎化の重要性、SaMD 該当性

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- 本シナリオのコード: リポジトリのライセンスに従う
- **UCI HAR データセット**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — 出典 Anguita et al. 2013, UCI Machine Learning Repository ([DOI](https://doi.org/10.24432/C54S4K))

## 免責

**本教材のモデルは教育・研究用の活動分類器であり、医療機器ではありません。診断、治療方針の決定、患者監視、安全上重要な判断には使用しないでください。**
臨床応用には日本では医療機器プログラム (SaMD)、EU では MDR、米国では FDA の枠組みに従った規制対応が必要です。詳細は [docs/07-ethics-and-limits.md](docs/07-ethics-and-limits.md) を参照してください。
