# 01 — 転移学習: 事前学習済み ResNet で少数データ分類

**対象**: ImageNet 事前学習モデルを **自分の少量データセット** に適応させたい農学・環境系研究者
**目標**: torchvision の ResNet18 (ImageNet 事前学習) のバックボーンを凍結し、**分類ヘッドのみ再学習**する定番手法を体験。デモは Oxford Flowers102 (102 種の花分類、公開データ、~330MB) — 農学の実データ (葉病害、雑草分類、作物種同定) にもそのまま適用できるテンプレート
**手法**: `torchvision.models.resnet18(weights=IMAGENET1K_V1)` + Linear head → 5-class subset

> [!NOTE]
> 完全にローカル CPU で完結。初回のみ Flowers102 (~330MB) と ResNet18 重み (~44MB) を自動ダウンロード。

## 全体像

```
src/train.py --epochs 8 --n-classes 5

   ├→ Flowers102 データセットから 5 クラス選択 (~200 画像)
   ├→ ResNet18 (ImageNet 事前学習) をロード、backbone を eval()+freeze
   ├→ 最終 fc 層のみ nn.Linear(512, 5) に置換して学習
   ├→ 検証精度を epoch ごとにログ
   └→ outputs/
        ├── best_model.pt
        ├── loss_acc.png
        └── confusion_matrix.png
```

## クイックスタート

```bash
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt

python src/train.py --epochs 8 --n-classes 5 --seed 42
python src/evaluate.py --model outputs/best_model.pt
```

## タスク

- **データ**: Oxford 102 Flower Category Dataset (Nilsback & Zisserman 2008)
- **サブサンプル**: 先頭 5 クラスのみ使用 → 学習 ~150, val ~40, test ~50 画像
- **入力**: 224×224 RGB (ImageNet 標準)
- **モデル**: ResNet18 backbone (11.7M params, 全 frozen) + Linear(512→5) head (2.5K params)

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| モデル | torchvision `resnet18(weights=IMAGENET1K_V1)` | 軽量 (44MB), CPU で 1 秒/バッチ |
| 学習方針 | backbone freeze, head only | 少データで overfit 回避、CPU で高速 |
| データ | `torchvision.datasets.Flowers102` | 自動ダウンロード、ラベル整備済み |
| 前処理 | ImageNet 標準 (Resize 256 → CenterCrop 224 → Normalize) | 事前学習時と統計を揃える |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [転移学習の考え方](docs/02-transfer-learning.md)
3. [学習](docs/03-train.md)
4. [結果の解釈](docs/04-understand-results.md)
5. [自前データへの適用](docs/05-your-data.md) — PlantVillage, 雑草分類等
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md)

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- Flowers102: Oxford VGG (研究利用フリー)
- ResNet18 weights: BSD (torchvision)
- コード: リポジトリのライセンス

## 免責

**本教材は転移学習のパターン学習用**。実際の農作物病害・雑草判定に転用する場合、以下が必須:
- 撮影条件 (照明・角度・カメラ機種) を統一
- クラス不均衡下では balanced sampling or class weight
- **誤判定が農家の経済損失に直結する用途** では、agronomist との共同検証を必ず経る
