"""学習済み PPO モデルを CartPole で走らせて平均リターンを報告する."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True, help="学習済み .zip")
    p.add_argument("--episodes", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--deterministic", action="store_true", default=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    env = Monitor(gym.make("CartPole-v1"))
    env.reset(seed=args.seed)
    model = PPO.load(str(args.model), env=env)
    mean_r, std_r = evaluate_policy(
        model, env, n_eval_episodes=args.episodes, deterministic=args.deterministic
    )
    print(f"episodes={args.episodes}  mean={mean_r:.2f} ± {std_r:.2f}  solved={mean_r >= 475}")
    env.close()


if __name__ == "__main__":
    main()
