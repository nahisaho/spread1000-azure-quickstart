# 05 — 別環境で試す

## MountainCar-v0

離散行動 3 択、報酬がスパース (山頂到達時のみ 0)。CartPole より難しい。

```python
env = gym.make("MountainCar-v0")
# train.py の "CartPole-v1" を書き換え
```

- `--timesteps 200000` 程度必要
- `--gamma 0.99` を維持

## LunarLander-v2

`pip install gymnasium[box2d]` が必要 (別途)。連続空間 8 次元、離散 4 行動 (左/右/メイン噴射/無)。

```bash
pip install "gymnasium[box2d]==1.3.0"
```

```python
env = gym.make("LunarLander-v2")
# 200000 step あたりで 200+ を狙う
```

## 連続行動空間 (Pendulum-v1)

`Pendulum-v1` は行動が連続 1 次元 (-2 to 2 のトルク)。**PPO は連続行動もそのまま扱える**:

```python
env = gym.make("Pendulum-v1")
# MlpPolicy は自動で連続 policy (Gaussian) を選ぶ
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
