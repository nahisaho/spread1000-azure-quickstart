# 機械・社会基盤・エネルギー工学 (Mechanical / Civil / Energy Engineering)

**分野規模**: SPReAD-1000 のうち **32 課題**

## 3 つのクイックスタート

| # | シナリオ | 手法 | 実行環境 | 所要 |
|---|---|---|---|---|
| [01](01-pinns-heat/) | PINNs で 1D 熱伝導 | 座標入力 MLP + 自動微分 + PDE 残差損失 | ノート PC (CPU) | 10 分 |
| [02](02-rl-cartpole/) | 強化学習 CartPole | Stable-Baselines3 PPO + Gymnasium | ノート PC (CPU) | 5 分 |
| [03](03-vibration-anomaly-ae/) | 振動信号異常検知 | 1D Conv Autoencoder + 再構成誤差閾値 | ノート PC (CPU) | 5 分 |

## 進め方

1. まず [01](01-pinns-heat/) で **物理制約付き NN** の考え方を体験
2. [02](02-rl-cartpole/) で **試行錯誤で学習するエージェント** を動かす
3. [03](03-vibration-anomaly-ae/) で **教師なし異常検知** を試す

いずれも **合成データ or ライブラリ内蔵** のため、追加データ入手は不要です。
