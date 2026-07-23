# 03 — 学習

## 実行

```bash
python src/train.py --timesteps 50000 --seed 42
```

## CLI オプション

| フラグ | 既定値 | 説明 |
|---|---|---|
| `--timesteps` | 50_000 | 総 step 数 (env 全体で) |
| `--n-envs` | 4 | 並列環境数 |
| `--seed` | 42 | 乱数シード |
| `--lr` | 3e-4 | Adam 学習率 |
| `--n-steps` | 1024 | rollout 長 / env |
| `--batch-size` | 64 | ミニバッチサイズ |
| `--gamma` | 0.99 | 割引率 |
| `--report-freq` | 5000 | 進捗レポート step 間隔 |
| `--eval-freq` | 5000 | EvalCallback の評価間隔 |
| `--n-eval-episodes` | 10 | 評価エピソード数 |
| `--tensorboard` | off | `./tb_logs` に TB ログ出力 |

## 期待される進行

```
[model] PPO MlpPolicy | envs=4 | total_timesteps=50000
[step   5000] ep_rew_mean = 22.4
[step  10000] ep_rew_mean = 45.8
[step  20000] ep_rew_mean = 152.3
[step  30000] ep_rew_mean = 372.1
[step  40000] ep_rew_mean = 480.9
[step  50000] ep_rew_mean = 495.5
[eval] final deterministic: 500.0 ± 0.0  (goal ≥ 475)
```

## TensorBoard

```bash
python src/train.py --timesteps 50000 --tensorboard
tensorboard --logdir tb_logs
# http://localhost:6006
```

## 実行時間の目安

| CPU | 50k step |
|---|---|
| Apple M1 | ~2 分 |
| Intel i5 (8th gen, 4 core) | ~4 分 |

## 出力

- `outputs/ppo_cartpole.zip` — 最終モデル
- `outputs/best_model.zip` — 評価最良モデル (EvalCallback による)
- `outputs/learning_curve.png` — step vs 平均リターン
- `outputs/eval_metrics.json` — 最終評価 (mean/std, solved 判定)
