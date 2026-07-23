# 02 — データ準備

## UCI HAR データセットの概要

**出典**: Anguita et al. (2013) *A Public Domain Dataset for Human Activity Recognition Using Smartphones* (ESANN 2013)
**ライセンス**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
**入手先**: [UCI ML Repository dataset #240](https://archive.ics.uci.edu/dataset/240/)

| 項目 | 値 |
|---|---|
| 被験者数 | 30 名 (19〜48 歳、健康な成人) |
| 装着位置 | 腰 (Samsung Galaxy S II) |
| センサー | 3 軸加速度 + 3 軸ジャイロ |
| サンプリング | 50 Hz |
| 窓長 | 2.56 秒 = 128 サンプル、50% 重複 |
| チャネル | body_acc × 3 + body_gyro × 3 + total_acc × 3 = **9 ch** |
| クラス | WALKING, WALKING_UPSTAIRS, WALKING_DOWNSTAIRS, SITTING, STANDING, LAYING (6 クラス) |
| 総サンプル数 | 10,299 窓 |
| 公式 train | 7,352 窓 (21 被験者) |
| 公式 test | 2,947 窓 (**9 被験者、train と重複なし**) |

## `prepare_data.py` の動作

```bash
python src/prepare_data.py
```

1. `data/har.zip` に UCI 公式 ZIP (~58 MB) をダウンロード（キャッシュあり）
2. SHA-256 を計算して表示（初回のみ、破損検知の目安）
3. `data/UCI_HAR_Dataset/` に **安全に展開**（絶対パス・`..` 参照を持つエントリを拒否）
4. `train/Inertial Signals/` と `test/Inertial Signals/` から 9 チャネルを読み込み `(N, 9, 128)` 配列に整形
5. `subject_train.txt` / `subject_test.txt` を読み込み、**被験者 ID が train/test で重複しないことを検証** (assert)
6. `data/har_windows.npz` に保存
   - `X_train, y_train, subj_train, X_test, y_test, subj_test, activities`

## 出力

```
data/
├── har.zip                    # 58 MB (キャッシュ, 削除しても再 DL)
├── UCI_HAR_Dataset/           # 展開後 (~280 MB)
└── har_windows.npz            # ~57 MB, これのみ後続ステップで使用
```

## なぜ被験者独立性が重要か

同じ人の隣接した 2.56 秒窓は **50% オーバーラップ** しており、生波形もほぼ同一です。窓を単純にランダム分割すると、非常に似たデータが train/val/test の全てに混ざり、精度が現実の未知被験者性能から大幅に過大評価されます。

この問題は複数のバイオシグナル論文で指摘されています:

- [Dehghani et al. (2019), *Sensors*](https://www.mdpi.com/1424-8220/19/22/5026) — サブジェクト依存分割で精度が非現実的に高くなることを実証
- [Scheurer et al. (2020), *PMC7374316*](https://pmc.ncbi.nlm.nih.gov/articles/PMC7374316/) — 加速度計データで同様の指摘

`prepare_data.py` は **公式 test を触らず**、`train.py` は **公式 train 内で被験者単位に 4:1 分割** します（[docs/03-train.md](03-train.md) 参照）。

## トラブル

- **`urllib.error.HTTPError: 403`**: UCI サーバがミラー変更した場合。`--url` オプションはありませんが、ZIP を手動で DL して `data/har.zip` に置けば以降のステップは動きます
- **`unsafe zip entry`**: 悪意ある ZIP が検出された時のみ発生（通常発生しません）
- **`Inertial Signals not found`**: 展開後のフォルダ構造が想定と違う場合。DL した ZIP のサイズを確認し、破損していれば削除して再実行してください
