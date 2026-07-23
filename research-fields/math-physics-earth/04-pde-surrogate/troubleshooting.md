# トラブルシューティング

## FD 解が発散する (NaN)

- CFL 条件違反、`src/pde.py` の dt 計算を確認
- 拡散係数 D が小さすぎる/大きすぎる場合は自動選択が不安定

## Val relL2 が下がらない (0.2 以上で頭打ち)

- 学習不足: `--epochs 30`
- モデル容量: `TinyUNet(base=32)` に増やす
- Residual 学習の効果を確認 (train.py の `return x + self.out(d1)` が入っているか)

## Rollout がすぐに発散

- 1-step 精度が不十分な状態で累積誤差爆発
- `--k-step` を短くする (5 → 3)
- 学習を長く回す (`--epochs 30`)

## メモリ不足

- `--batch-size 8`
- `--n-train 16`

## 図が生成されない (X server なし)

- `matplotlib.use("Agg")` が train.py の import 前に設定されているか
