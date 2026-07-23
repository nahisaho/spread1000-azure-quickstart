"""
Stable-Baselines3 PPO で CartPole-v1 を学習する.

- Vectorized env (4 並列) で rollout
- 5000 step ごとに 10 エピソード評価しコールバックで最良モデル保存
- 学習曲線 (report ごとの平均リターン) を PNG で出力
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


class ProgressCallback(BaseCallback):
    """report_freq step ごとに平均リターンを stdout & memory に残す."""

    def __init__(self, report_freq: int = 5000):
        super().__init__()
        self.report_freq = report_freq
        self.steps: list[int] = []
        self.mean_returns: list[float] = []

    def _on_step(self) -> bool:
        if self.n_calls % self.report_freq != 0:
            return True
        # Monitor wrapper が終了時に ep_info_buffer (deque of {'r','l','t'}) を積む
        buf = getattr(self.model, "ep_info_buffer", None)
        if buf and len(buf) > 0:
            ep_rew_mean = float(np.mean([ep["r"] for ep in buf]))
            self.steps.append(self.num_timesteps)
            self.mean_returns.append(ep_rew_mean)
            if self.verbose > 0:
                print(f"[step {self.num_timesteps:6d}] ep_rew_mean = {ep_rew_mean:.1f}")
        return True


def make_env(seed: int, n_envs: int) -> SubprocVecEnv:
    def _fn(rank: int):
        def _init():
            env = gym.make("CartPole-v1")
            env = Monitor(env)
            env.reset(seed=seed + rank)
            return env
        return _init

    return SubprocVecEnv([_fn(i) for i in range(n_envs)])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--timesteps", type=int, default=50_000)
    p.add_argument("--n-envs", type=int, default=4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--n-steps", type=int, default=1024, help="PPO rollout length / env")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--report-freq", type=int, default=5000)
    p.add_argument("--eval-freq", type=int, default=5000, help="EvalCallback 周期 (step)")
    p.add_argument("--n-eval-episodes", type=int, default=10)
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--tensorboard", action="store_true", help="./tb_logs に TB ログ出力")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # subprocess vec env にはメイン guard が必須
    train_env = make_env(args.seed, args.n_envs)
    # EvalCallback 側の警告回避: eval も vec env にする
    eval_env = DummyVecEnv([lambda: Monitor(gym.make("CartPole-v1"))])

    tb_dir = str(ROOT / "tb_logs") if args.tensorboard else None

    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        gamma=args.gamma,
        seed=args.seed,
        verbose=0,
        tensorboard_log=tb_dir,
    )
    print(f"[model] PPO MlpPolicy | envs={args.n_envs} | total_timesteps={args.timesteps}")

    progress = ProgressCallback(report_freq=args.report_freq)
    progress.verbose = 1
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=str(out_dir),
        log_path=str(out_dir),
        eval_freq=max(args.eval_freq // args.n_envs, 1),  # SB3 は per-env step で数える
        n_eval_episodes=args.n_eval_episodes,
        deterministic=True,
        render=False,
        verbose=0,
    )

    model.learn(total_timesteps=args.timesteps, callback=[progress, eval_cb])

    # 最終モデル (best は EvalCallback が out_dir/best_model.zip に保存)
    final_path = out_dir / "ppo_cartpole.zip"
    model.save(str(final_path))

    # 手動最終評価 (deterministic)
    from stable_baselines3.common.evaluation import evaluate_policy

    mean_ret, std_ret = evaluate_policy(
        model, eval_env, n_eval_episodes=20, deterministic=True
    )
    print(f"[eval] final deterministic: {mean_ret:.1f} ± {std_ret:.1f}  (goal ≥ 475)")

    # 学習曲線
    if progress.steps:
        plt.figure(figsize=(7, 4))
        plt.plot(progress.steps, progress.mean_returns, marker="o", linewidth=2)
        plt.axhline(475, color="tab:red", linestyle="--", label="solve threshold (475)")
        plt.xlabel("timesteps")
        plt.ylabel("mean episode return (rollout window)")
        plt.title("PPO on CartPole-v1")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "learning_curve.png", dpi=120)
        plt.close()

    with (out_dir / "eval_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "final_mean_return": round(float(mean_ret), 2),
                "final_std_return": round(float(std_ret), 2),
                "total_timesteps": args.timesteps,
                "seed": args.seed,
                "solved_threshold": 475,
                "solved": bool(mean_ret >= 475),
            },
            f,
            indent=2,
        )

    train_env.close()
    eval_env.close()
    print(f"[train] saved → {final_path}, {out_dir}/best_model.zip, learning_curve.png")


if __name__ == "__main__":
    main()
