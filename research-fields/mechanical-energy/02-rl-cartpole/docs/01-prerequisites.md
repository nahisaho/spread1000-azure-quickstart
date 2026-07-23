# 01 — 前提条件

## 環境

- Python 3.10 以上 (3.12 推奨)
- Windows / macOS / Linux
- CPU 4 コア以上推奨 (並列 rollout)

## インストール

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Stable-Baselines3 は PyTorch を依存関係として自動で入れます (CPU 版)。
既に PyTorch GPU 版を入れている場合はそちらが使われます。

## 動作確認

```bash
python -c "import gymnasium as gym; env=gym.make('CartPole-v1'); print(env.observation_space, env.action_space)"
```

出力例:
```
Box([-4.8 -inf -0.41887903 -inf], [4.8 inf 0.41887903 inf], (4,), float32) Discrete(2)
```
