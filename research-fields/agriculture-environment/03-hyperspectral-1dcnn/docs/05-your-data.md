# 05 — 自前データへの適用

## モード一覧

| モード | データ | コマンド例 |
|---|---|---|
| `synthetic` | 合成 6-class (デフォルト) | `python src/train.py` |
| `indianpines` | 実 Indian Pines (要初回インターネット) | `python src/train.py --mode indianpines` |
| `custom` | 自前 NPY/CSV | `python src/train.py --mode custom --data-root path/` |

---

## indianpines モード

### データ出典とライセンス

Indian Pines シーンは 1992 年 6 月に NASA/JPL の AVIRIS センサーがインディアナ州
農地上空で取得したデータです。処理済み `.mat` ファイルは Purdue 大学の
David Landgrebe 教授グループが公開し、学術研究で広く使われています。

**引用義務**: 研究・発表に使う場合は以下を引用してください:
> Landgrebe, D. (2003). *Signal Theory Methods in Multispectral Remote Sensing*.
> Wiley-Interscience.

**ライセンス注意**: `.mat` ファイルの正式なオープンライセンスは文書化されていません。
非研究用途 (商用・再配布等) の場合は Purdue 大学に問い合わせて確認してください。
本ツールは研究・教育目的のみで使用してください。

### ダウンロード (自動)

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/03-hyperspectral-1dcnn"
cd "$SCENARIO_DIR"
test -f src/train.py || { echo "abort: wrong directory"; exit 1; }

# 初回実行時に data/ へ自動ダウンロード (インターネット必要)
python src/train.py --mode indianpines \
    --split-strategy disjoint_patch \
    --balance weighted_ce \
    --epochs 30
```

### 手動ダウンロード (ミラー不安定時)

以下 URL から手動取得して `data/` に置いてください:
```
# ミラー (2026 年時点; 利用不可の場合は Kaggle / Zenodo を検索)
https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat
https://www.ehu.eus/ccwintco/uploads/c/c4/Indian_pines_gt.mat
```

```bash
# 取得後
python src/train.py --mode indianpines --data-root data/
```

---

## custom モード

### ディレクトリ構成

```
data-root/
  X.npy           # (N, B) float32 — N ピクセル × B バンド
  y.npy           # (N,) int64     — 0-indexed クラスラベル
  class_names.txt # クラス名 1 行 1 名 (省略可)
  coords.npy      # (N, 2) int32 [row, col]  ← disjoint_patch split に必要
```

### 空間分割について

```bash
# 空間座標あり → disjoint_patch 推奨 (空間リーク防止)
python src/train.py --mode custom --data-root path/to/ \
    --split-strategy disjoint_patch

# 座標なし → random_pixel (警告が出る; 実データには非推奨)
python src/train.py --mode custom --data-root path/to/ \
    --split-strategy random_pixel --allow-random-pixel-split
```

---

## 他の公開ハイパースペクトルデータセット

| データセット | サイズ | クラス数 | ドメイン |
|---|---|---|---|
| Indian Pines | 145×145×200 | 16 | 農地 (米中西部) |
| Salinas | 512×217×204 | 16 | 農地 (加州) |
| Pavia University | 610×340×103 | 9 | 都市 |
| Houston 2013 | 349×1905×144 | 15 | 都市+植生 |
| KSC | 512×614×176 | 13 | 湿地植生 |

---

## 精度向上のヒント

- Indian Pines 等では **クラス不均衡が大きい** (Oats 20, Soybean 2455) →
  `--balance weighted_ce` または `focal`
- **disjoint_patch** で空間リークを防ぐ (デフォルト)
- PCA で 200 → 30 バンドに削減後に 1D-CNN も有効
- 空間コンテキストが必要なら 2D-CNN で 5×5 patch を入力に
