# 02 — RL の考え方 (5 分)

## 4 つの構成要素

| 要素 | CartPole での具体例 |
|---|---|
| **状態 (state)** | 4 次元ベクトル: (カート位置, カート速度, ポール角度, ポール角速度) |
| **行動 (action)** | 2 択: 左 / 右 に押す |
| **報酬 (reward)** | 1 step 生き延びるごとに +1 |
| **方策 (policy)** π | 状態 → 行動の確率分布。ニューラルネット (MlpPolicy) |

## ループ

```
        ┌──────────┐
   ┌───→│ Env      │
   │    │(CartPole)│
   │    └────┬─────┘
   │         │ state s, reward r
   │         ↓
   │    ┌──────────┐
   │    │ Policy π │  action a ~ π(s)
   │    └────┬─────┘
   │         │
   └─────────┘
```

- **1 エピソード** = ポールが倒れる or 500 step まで
- **リターン** = 1 エピソードで受け取った報酬の合計 (最大 500)
- **目標**: エピソード平均リターンを最大化する π を学習

## PPO (Proximal Policy Optimization) の直感

- **actor-critic**: actor がπ、critic が価値関数 V(s)
- 「今の π からあまり離れないように」少しずつ更新 (これが "Proximal")
- **clip 目的関数**: 更新が暴れないよう比率を \[1-ε, 1+ε\] に clip
- **利点**: ハイパラに寛容、on-policy で安定、実装が普及

## Rollout & Update サイクル

1. Rollout: N_envs × n_steps ステップ = 4 × 1024 = 4096 サンプル収集
2. Update: そのバッチを batch_size=64 で n_epochs (SB3 デフォルト 10) 回学習
3. 破棄して次の rollout へ (on-policy)

CartPole ではだいたい **20〜50k step で 475 到達** します。
