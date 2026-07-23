# 04 — 結果の読み方

## learning_curve.png

- 横軸: total timesteps
- 縦軸: 直近 rollout ウィンドウの平均エピソードリターン
- 赤破線: solve 閾値 (475)

**健全なパターン**: 5k までは 20〜30、10k で 100 越え、20〜30k で 400 超え、40k で 475 越え。

**失敗パターン**:
- ずっと 20 付近から動かない → 乱数シードの悪運、`--seed 0` などを試す
- 200 前後で停滞して落ちる → `--n-steps 2048` に増やす
- ノコギリ状に振動 → `--lr 1e-4` に下げる

## eval_metrics.json

```json
{
  "final_mean_return": 500.0,
  "final_std_return": 0.0,
  "total_timesteps": 50000,
  "seed": 42,
  "solved_threshold": 475,
  "solved": true
}
```

`solved: true` になれば CartPole クリア。

## rollout/ep_rew_mean vs deterministic 評価

- 学習中の `ep_rew_mean` は **確率的** に行動選択したときの平均 (探索が入っている)
- 最終評価は `deterministic=True` で argmax 行動 (探索なし) を選ぶため、値は少し高くなる
- 両者の差が大きい (探索時 200, det 500) 場合は policy entropy がまだ高い状態

## Best vs Final モデル

- `best_model.zip`: `EvalCallback` が保存した最良評価スコアのモデル
- `ppo_cartpole.zip`: 学習ループ終了時点のモデル
- 一般には **best を推論に使う**
