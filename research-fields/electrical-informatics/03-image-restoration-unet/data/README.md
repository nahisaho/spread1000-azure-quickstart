# data/

このディレクトリは `src/generate_data.py` の実行によって自動生成されます。**リポジトリにはコミットしません** (`.gitignore` 済み)。

## 実行後の構成

```
data/
├── train/
│   ├── 0000.npz    # ← 各サンプル {"clean": (1,H,W) float32, "noisy": (1,H,W) float32}
│   └── ...
├── val/
│   ├── 0000.npz
│   └── ...
└── samples/
    └── preview.png    # 生成画像の目視確認用
```

## 生成データの仕様

| キー | dtype | shape | 値域 |
|---|---|---|---|
| `clean` | float32 | (1, 128, 128) | [0, 1] |
| `noisy` | float32 | (1, 128, 128) | [0, 1] (`clean + N(0, σ)` を clip) |

- σ (`--noise-sigma`, 既定 0.10) の Gaussian ノイズを clean に加算
- clean 画像は幾何プリミティブ (矩形・円・直線・グラデーション) + Gaussian smoothing の合成 (詳細: [docs/02-generate-data.md](../docs/02-generate-data.md))

## ライセンス

**完全合成のためライセンス制約はありません**。生成コード (`src/generate_data.py`) の再頒布はリポジトリのライセンスに従います。
