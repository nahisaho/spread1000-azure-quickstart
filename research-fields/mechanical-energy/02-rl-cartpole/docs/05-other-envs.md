# 05 — 別環境で試す

`train.py` と `evaluate.py` は `--env-id` 引数で任意の Gymnasium 環境に切り替えられます。  
環境 ID は `eval_metrics.json` にも記録されるため、`evaluate.py` は自動でその環境を再現します。

## MountainCar-v0

各 step に -1 の時間最小化型報酬 (山頂到達まで step 数を最小にする)。CartPole より難しい。

```bash
python src/train.py --env-id MountainCar-v0 --timesteps 200000 \
    --allow-long-run --output-dir outputs/mountaincar
python src/evaluate.py --model outputs/mountaincar/ppo_cartpole.zip
```

- `--timesteps 200000` 程度必要 (PPO は探索が苦手なため解けないこともある)
- `--gamma 0.99` を維持

## LunarLander-v3

`pip install gymnasium[box2d]` が必要 (別途)。連続空間 8 次元、離散 4 行動 (左/右/メイン噴射/無)。

```bash
pip install "gymnasium[box2d]==1.3.0"

python src/train.py --env-id LunarLander-v3 --timesteps 500000 \
    --allow-long-run --output-dir outputs/lunar
python src/evaluate.py --model outputs/lunar/ppo_cartpole.zip
```

## 連続行動空間 (Pendulum-v1)

`Pendulum-v1` は行動が連続 1 次元 (-2 to 2 のトルク)。**PPO は連続行動もそのまま扱える**:

```bash
python src/train.py --env-id Pendulum-v1 --timesteps 100000 \
    --output-dir outputs/pendulum
python src/evaluate.py --model outputs/pendulum/ppo_cartpole.zip
```

## カスタム環境

Gymnasium API に準拠して `reset()` / `step()` を実装:

```python
class MyEnv(gym.Env):
    metadata = {"render_modes": []}
    def __init__(self):
        self.action_space = gym.spaces.Discrete(2)
        self.observation_space = gym.spaces.Box(low=-1, high=1, shape=(4,), dtype=np.float32)
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        return obs, {}
    def step(self, action):
        return obs, reward, terminated, truncated, info
```

## 別アルゴリズム

- **A2C**: PPO の前身、シンプルで速いが不安定
- **DQN**: 離散行動限定、リプレイバッファ使用、値ベース
- **SAC**: 連続行動最強クラス、off-policy
- **DDPG / TD3**: 連続行動用の決定的方策

すべて SB3 で `from stable_baselines3 import SAC` の形で呼べます。
