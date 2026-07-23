# 07 — 倫理と限界

## RL は実世界応用でつまづきやすい

### Sim-to-Real Gap

- シミュレータで完璧に動く方策が、実機で **壊滅的に失敗** することは常態
- 物理パラメータ (摩擦、質量、遅延、ノイズ) の微妙な差が累積
- 対策: Domain Randomization, System Identification, Residual RL

### 報酬設計の罠 (Reward Hacking)

- 「速度を最大化しろ」→ カメラを回転させて相対速度を稼ぐ、等の想定外挙動
- 「衝突しないで A へ行け」→ 動かないのが最適解 (衝突しないが到達もしない)
- 対策: shaping 報酬に依存しない、多目的評価、人間による safety review

### サンプル効率

- CartPole ですら 50k step (数万回の試行) 必要
- 実物ロボットで直接学習は非現実的。シミュレータ or off-policy + human demonstrations が実用

## 安全性が問われる用途

- 発電プラント制御、自動運転、医療機器 → PPO / DQN の直接デプロイは危険
- 必ず **safety filter (shielded RL, CBF)** で hard constraint を強制
- 認証 (IEC 61508, ISO 26262, FDA など) を持つ従来制御をベースラインに置き、RL は探索/最適化補助として使う

## 参考文献

- Schulman et al. (2017). *"Proximal Policy Optimization Algorithms"*, arXiv:1707.06347
- Sutton, Barto. *"Reinforcement Learning: An Introduction"*, 2nd ed., MIT Press
- Amodei et al. (2016). *"Concrete Problems in AI Safety"*, arXiv:1606.06565
