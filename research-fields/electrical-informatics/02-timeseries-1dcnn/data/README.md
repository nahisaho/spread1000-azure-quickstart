# data/

このディレクトリは `src/prepare_data.py` の実行によって自動生成されます。**リポジトリにはコミットしません** (`.gitignore` 済み)。

## 期待される内容 (実行後)

```
data/
├── har.zip                    # ~58 MB, UCI 公式 ZIP (キャッシュ)
├── UCI_HAR_Dataset/           # ~280 MB, 展開後のフォルダ
│   ├── activity_labels.txt
│   ├── train/
│   │   ├── Inertial Signals/
│   │   ├── subject_train.txt
│   │   └── y_train.txt
│   └── test/
│       ├── Inertial Signals/
│       ├── subject_test.txt
│       └── y_test.txt
└── har_windows.npz            # ~57 MB, 変換済み配列 (後続ステップで使用)
```

## har_windows.npz の中身

`np.load()` で読める辞書ライクなオブジェクト:

| キー | dtype | shape | 説明 |
|---|---|---|---|
| `X_train` | float32 | (7352, 9, 128) | 公式 train 生波形 |
| `y_train` | int64 | (7352,) | 0〜5 のクラス |
| `subj_train` | int64 | (7352,) | 被験者 ID (1〜30 のうち 21 名) |
| `X_test` | float32 | (2947, 9, 128) | 公式 test 生波形 |
| `y_test` | int64 | (2947,) | 0〜5 のクラス |
| `subj_test` | int64 | (2947,) | 被験者 ID (train と重複なしの 9 名) |
| `activities` | str | (6,) | クラス名 (WALKING, WALKING_UPSTAIRS, ...) |

## チャネル順序 (X_* の 2 軸目)

`prepare_data.py:SIGNAL_NAMES` で定義:

```
0: body_acc_x    # 加速度から重力成分を除いた x 軸
1: body_acc_y
2: body_acc_z
3: body_gyro_x   # ジャイロスコープ x 軸
4: body_gyro_y
5: body_gyro_z
6: total_acc_x   # 加速度 (重力を含む) x 軸
7: total_acc_y
8: total_acc_z
```

いずれも 50 Hz サンプリング、2.56 秒 = 128 サンプル、50% オーバーラップ窓済み。

## ライセンス

**CC BY 4.0** — 出典表示が必要です。詳細は [docs/07-ethics-and-limits.md](../docs/07-ethics-and-limits.md) を参照。
