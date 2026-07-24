"""
Stable-Baselines3 PPO で任意の Gymnasium 環境を学習する.

- Vectorized env (n_envs 並列) で rollout
- 5000 step ごとに評価: 平均リターン (EvalCallback + ProgressCallback)
- 最良モデル保存 (EvalCallback → best_model.zip)
- 学習曲線 (report ごとの平均リターン) を PNG で出力
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv

from _argtypes import bounded_int, finite_float, positive_float, positive_int

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"


class ProgressCallback(BaseCallback):
    """report_freq timesteps ごとに平均リターンを stdout & memory に残す."""

    def __init__(self, report_freq: int = 5000):
        super().__init__()
        self.report_freq = report_freq
        self._last_report = 0
        self.steps: list[int] = []
        self.mean_returns: list[float] = []

    def _on_step(self) -> bool:
        if self.num_timesteps - self._last_report < self.report_freq:
            return True
        self._last_report = self.num_timesteps
        # Monitor wrapper が終了時に ep_info_buffer (deque of {'r','l','t'}) を積む
        buf = getattr(self.model, "ep_info_buffer", None)
        if buf and len(buf) > 0:
            ep_rew_mean = float(np.mean([ep["r"] for ep in buf]))
            self.steps.append(self.num_timesteps)
            self.mean_returns.append(ep_rew_mean)
            if self.verbose > 0:
                print(f"[step {self.num_timesteps:6d}] ep_rew_mean = {ep_rew_mean:.1f}")
        return True


def make_train_env(env_id: str, seed: int, n_envs: int):
    """訓練用 VecEnv を作成する. n_envs==1 のときは DummyVecEnv を使う."""
    def _fn(rank: int):
        def _init():
            env = gym.make(env_id)
            env = Monitor(env)
            env.reset(seed=seed + rank)
            return env
        return _init

    if n_envs == 1:
        return DummyVecEnv([_fn(0)])
    return SubprocVecEnv([_fn(i) for i in range(n_envs)])


def make_eval_env(env_id: str, seed: int) -> DummyVecEnv:
    """評価用シード固定 DummyVecEnv を作成する."""
    e = DummyVecEnv([lambda: Monitor(gym.make(env_id))])
    e.seed(seed)
    return e


def _get_git_info() -> dict:
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        )
    except Exception:
        sha = "unknown"
        dirty = None
    return {"git_sha": sha, "git_dirty": dirty}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="PPO で Gymnasium 環境を学習する"
    )
    p.add_argument("--env-id", type=str, default="CartPole-v1", help="Gymnasium 環境 ID")
    p.add_argument(
        "--timesteps",
        type=bounded_int("--timesteps", 1, 2_000_000),
        default=50_000,
        help="学習ステップ数 (1..2,000,000)",
    )
    p.add_argument(
        "--n-envs",
        type=bounded_int("--n-envs", 1, 16),
        default=4,
        help="並列環境数 (1..16)",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--lr", type=positive_float("--lr"), default=3e-4)
    p.add_argument("--n-steps", type=int, default=1024, help="PPO rollout length / env")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument(
        "--report-freq",
        type=positive_int("--report-freq"),
        default=5000,
        help="進捗レポート間隔 (timesteps, ≥1)",
    )
    p.add_argument(
        "--eval-freq",
        type=int,
        default=5000,
        help="EvalCallback 周期 (timesteps)",
    )
    p.add_argument(
        "--n-eval-episodes",
        type=bounded_int("--n-eval-episodes", 1, 1000),
        default=10,
    )
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--tensorboard", action="store_true", help="./tb_logs に TB ログ出力")
    p.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="PyTorch デバイス (default: cpu)",
    )
    p.add_argument(
        "--allow-long-run",
        action="store_true",
        help="--timesteps > 500,000 を許可する",
    )
    p.add_argument(
        "--require-solved",
        action="store_true",
        help="閾値未達で exit 2",
    )
    p.add_argument(
        "--min-return",
        type=finite_float("--min-return"),
        default=None,
        help="--require-solved の閾値上書き (gym.spec の reward_threshold をバイパス)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.timesteps > 500_000 and not args.allow_long_run:
        print(
            f"[error] --timesteps {args.timesteps} > 500,000. "
            "Pass --allow-long-run to proceed.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    out_dir = args.output_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # subprocess vec env にはメイン guard が必須
    train_env = make_train_env(args.env_id, args.seed, args.n_envs)
    # コールバック用評価環境 (seed = args.seed + 10000)
    eval_env = make_eval_env(args.env_id, args.seed + 10000)
    # 最終評価は独立した固定シード環境を使う (コールバック環境と混在させない)
    final_eval_env = make_eval_env(args.env_id, args.seed + 20000)

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
        device=args.device,
    )
    print(
        f"[model] PPO MlpPolicy | env={args.env_id} | envs={args.n_envs} "
        f"| total_timesteps={args.timesteps} | device={args.device}"
    )

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

    # 最終評価: コールバック環境とは別の固定シード環境を使用
    mean_ret, std_ret = evaluate_policy(
        model, final_eval_env, n_eval_episodes=20, deterministic=True
    )

    # 成功閾値: --min-return > gym.spec.reward_threshold > 475 の優先度
    spec = gym.spec(args.env_id)
    threshold: float
    if args.min_return is not None:
        threshold = args.min_return
    elif spec.reward_threshold is not None:
        threshold = float(spec.reward_threshold)
    else:
        threshold = 475.0

    solved = bool(
        np.isfinite(float(mean_ret))
        and np.isfinite(float(std_ret))
        and float(mean_ret) >= threshold
    )
    print(
        f"[eval] final deterministic: {mean_ret:.1f} ± {std_ret:.1f}  "
        f"(goal ≥ {threshold})"
    )

    # 学習曲線
    if progress.steps:
        plt.figure(figsize=(7, 4))
        plt.plot(progress.steps, progress.mean_returns, marker="o", linewidth=2)
        plt.axhline(
            threshold,
            color="tab:red",
            linestyle="--",
            label=f"solve threshold ({threshold})",
        )
        plt.xlabel("timesteps")
        plt.ylabel("mean episode return (rollout window)")
        plt.title(f"PPO on {args.env_id}")
        plt.grid(alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "learning_curve.png", dpi=120)
        plt.close()

    # プロベナンス情報
    import stable_baselines3
    import torch

    git_info = _get_git_info()
    provenance = {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "stable_baselines3": stable_baselines3.__version__,
        "gymnasium": gym.__version__,
        "torch": torch.__version__,
        "numpy": np.__version__,
        "device": args.device,
        "deterministic": True,
        **git_info,
    }

    # PPO は n_envs × n_steps 境界に切り上げる → 実績ステップを記録
    actual_timesteps = model.num_timesteps

    with (out_dir / "eval_metrics.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "env_id": args.env_id,
                "final_mean_return": (
                    round(float(mean_ret), 2) if np.isfinite(float(mean_ret)) else None
                ),
                "final_std_return": (
                    round(float(std_ret), 2) if np.isfinite(float(std_ret)) else None
                ),
                "total_timesteps_requested": args.timesteps,
                "total_timesteps_actual": actual_timesteps,
                "seed": args.seed,
                "solved_threshold": threshold,
                "solved": solved,
                "provenance": provenance,
            },
            f,
            indent=2,
        )

    train_env.close()
    eval_env.close()
    final_eval_env.close()

    saved_candidates = [
        final_path,
        out_dir / "best_model.zip",
        out_dir / "learning_curve.png",
    ]
    existing = [p for p in saved_candidates if p.exists()]
    print(f"[train] saved → {', '.join(str(p) for p in existing)}")
    print(
        f"[note]  PPO rounds up to n_envs × n_steps boundary; "
        f"actual timesteps = {actual_timesteps}"
    )

    if args.require_solved and not solved:
        print(
            f"[fail] mean_return {mean_ret:.1f} < threshold {threshold}. Exiting 2.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
