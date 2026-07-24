"""学習済み PPO モデルを Gymnasium 環境で走らせて平均リターンを報告する."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.monitor import Monitor

from _argtypes import bounded_int


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="学習済みモデルを評価する")
    p.add_argument("--model", type=Path, required=True, help="学習済み .zip")
    p.add_argument(
        "--episodes",
        type=bounded_int("--episodes", 1, 1000),
        default=20,
    )
    p.add_argument("--seed", type=int, default=0)
    p.add_argument(
        "--deterministic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="決定的行動 (--no-deterministic で確率的)",
    )
    p.add_argument(
        "--env-id",
        type=str,
        default=None,
        help="環境 ID (未指定: eval_metrics.json の env_id を参照, fallback: CartPole-v1)",
    )
    p.add_argument(
        "--expected-sha256",
        type=str,
        default=None,
        help="モデル .zip の SHA-256 ハッシュ (16 進) で整合性を検証",
    )
    return p.parse_args()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    # HIGH-4: cloudpickle 警告
    print(
        "[warn] SB3 archives may contain cloudpickle. "
        "Load only models you produced or SHA-256-verified from a trusted source.",
        file=sys.stderr,
    )

    args = parse_args()

    # HIGH-4: 任意の SHA-256 検証
    if args.expected_sha256:
        actual = _sha256_file(args.model)
        if not hmac.compare_digest(actual.lower(), args.expected_sha256.lower()):
            print(
                f"[error] SHA-256 mismatch.\n"
                f"  expected: {args.expected_sha256}\n"
                f"  actual:   {actual}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        print(f"[ok] SHA-256 verified: {actual}", file=sys.stderr)

    # HIGH-5: env_id を metadata から読む
    env_id = args.env_id
    if env_id is None:
        metrics_path = args.model.parent / "eval_metrics.json"
        if metrics_path.exists():
            with metrics_path.open(encoding="utf-8") as f:
                meta = json.load(f)
            env_id = meta.get("env_id", "CartPole-v1")
        else:
            env_id = "CartPole-v1"

    env = Monitor(gym.make(env_id))
    env.reset(seed=args.seed)
    model = PPO.load(str(args.model), env=env)
    mean_r, std_r = evaluate_policy(
        model, env, n_eval_episodes=args.episodes, deterministic=args.deterministic
    )

    spec = gym.spec(env_id)
    threshold = float(spec.reward_threshold) if spec.reward_threshold is not None else 475.0
    print(
        f"env={env_id}  episodes={args.episodes}  "
        f"mean={mean_r:.2f} ± {std_r:.2f}  solved={mean_r >= threshold}"
    )
    env.close()


if __name__ == "__main__":
    main()
