# 05 — 自前データへの適用

## 作業ディレクトリの確認

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/01-transfer-plant-disease"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "wrong dir; abort"; exit 1; }
```

## ディレクトリ構造

`torchvision.datasets.ImageFolder` に準拠した `train/`, `val/`, `test/` を用意し、`--data-root` で指定する (HIGH 5):

```
my_plants/
├── train/
│   ├── healthy/          # class 0
│   │   ├── 001.jpg
│   │   └── ...
│   ├── rust/             # class 1
│   └── blight/           # class 2
├── val/
│   ├── healthy/
│   ├── rust/
│   └── blight/
└── test/
    ├── healthy/
    ├── rust/
    └── blight/
```

## `--data-root` を使った学習 (HIGH 5)

```bash
python src/train.py \
  --data-root my_plants \
  --epochs 15 \
  --seed 42

python src/evaluate.py \
  --model outputs/best_model.pt \
  --data-root my_plants
```

- `class_to_idx` は `train/` のサブフォルダ名から自動生成
- `val/`, `test/` が `train/` に存在しないクラスを含む場合はエラーで停止
- クラス名は checkpoint に `class_names` として保存され、evaluate.py が自動読込 (Flowers102 ハードコードなし)

> [!WARNING]
> コードを手書き変更して Flowers102 以外のデータを読み込む方法 (旧ドキュメントに記載) は不要です。`--data-root` を使ってください。

## グループ対応スプリット (HIGH 6) — PlantVillage 等を使う場合の注意

PlantVillage (mohanty 配布版) は **同一葉の複数枚撮影**が含まれる。単純なランダム分割では同一葉の画像が train と test に混入し、**実際の汎化性能を過大評価**する。

### スプリットマニフェスト形式

```csv
file_path,class,group_id
data/train/healthy/leaf001_a.jpg,healthy,leaf001
data/train/healthy/leaf001_b.jpg,healthy,leaf001
data/val/rust/leaf042_a.jpg,rust,leaf042
```

- `group_id` は 葉・株・圃場・農園・撮影セッションなど独立単位
- **同一グループが train/val/test に分散しないよう**グループ単位で分割する
- 完全な品種 / 農園 / 地域を hold-out することで「未知条件への汎化」を測定できる

### 重複画像検出スクリプト

```python
import hashlib, pathlib, sys

def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

roots = {"train": [], "val": [], "test": []}
for split in roots:
    roots[split] = {sha256(p): str(p) for p in pathlib.Path(f"my_plants/{split}").rglob("*.jpg")}

for split_a, hashes_a in roots.items():
    for split_b, hashes_b in roots.items():
        if split_a >= split_b:
            continue
        dupes = set(hashes_a) & set(hashes_b)
        if dupes:
            print(f"[WARN] {len(dupes)} duplicate(s) between {split_a} and {split_b}:")
            for h in dupes:
                print(f"  {hashes_a[h]}  ==  {hashes_b[h]}")
            sys.exit(1)
print("[OK] no duplicates across splits")
```

## クラス不均衡対策 (HIGH 7)

```bash
# 不均衡データ時は weighted-loss + val_macro_f1 を推奨
python src/train.py \
  --data-root my_plants \
  --balance weighted-loss \
  --best-metric val_macro_f1 \
  --epochs 15
```

| `--balance` | 効果 | 注意 |
|---|---|---|
| `none` (既定) | 通常学習 | 均衡データ向け |
| `weighted-loss` | クラス重みを CrossEntropyLoss に渡す | 不均衡時推奨 |
| `weighted-sampler` | minority class を oversampling | `weighted-loss` との併用不可 |

- `--best-metric val_macro_f1` でチェックポイント選択基準をマクロ F1 に変更
- 学習前にクラスごとのサンプル数がログに出力される

## Fine-tuning (HIGH 8)

1000 サンプル以上ある場合は `--fine-tune` で layer4 + fc を同時学習:

```bash
python src/train.py \
  --data-root my_plants \
  --fine-tune \
  --scheduler cosine \
  --epochs 20 \
  --patience 5 \
  --balance weighted-loss \
  --best-metric val_macro_f1
```

- `layer4` lr = `--lr` × 0.1、`fc` lr = `--lr` (パラメータグループ)
- `--bn-train`: layer4 内の BatchNorm を train モードに (通常不要)
- `--scheduler cosine|step`: LR スケジューラ
- `--patience N`: N エポック改善なしで早期終了

## 公開データセット候補

| データセット | 用途 | サイズ | ライセンス |
|---|---|---|---|
| **PlantVillage (mohanty 配布版)** | 葉病害 38 種 | ~1.5GB | **CC BY-SA 3.0** — 派生物にも同一ライセンスと帰属表示が必要 |
| **DeepWeeds** | オーストラリアの雑草 8 種 | ~1GB | CC-BY |
| **iNaturalist Species** | 動植物 8000+ 種 | 30GB+ | CC-BY-NC |
| **CropDeep** | 稲作害虫 | ~500MB | 論文リポジトリ経由 |

> [!NOTE]
> **Oxford Flowers102** の公式ページには明示ライセンスなし。再配布・商用利用前に権利元 (Oxford VGG) へ許諾確認が必要。
