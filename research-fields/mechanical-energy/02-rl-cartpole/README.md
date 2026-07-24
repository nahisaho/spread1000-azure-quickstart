# 02 — 強化学習 CartPole (PPO)

**対象**: 強化学習 (RL) を教科書で学んだが実装したことがない機械・制御系研究者
**目標**: Gymnasium の古典タスク `CartPole-v1` を Stable-Baselines3 の PPO で学習し、**環境・エージェント・報酬** の 3 要素とハイパラの影響を数分で体験する
**手法**: PPO (Proximal Policy Optimization) — actor-critic 系の主力アルゴリズム、SB3 の推奨デフォルト

> [!NOTE]
> 完全にローカル CPU 完結。学習時間は 3〜5 分。GPU 不要。

## 全体像

```
src/train.py --timesteps 50000

   ├→ Vectorized Env (4 並列) で CartPole-v1 を回す
   ├→ MlpPolicy (2 層 64 unit) を PPO で更新
   ├→ 5000 step ごとに評価: 平均リターン
   └→ outputs/
        ├── ppo_cartpole.zip     # 学習済みモデル (最終)
        ├── best_model.zip       # EvalCallback が保存した最良モデル
        ├── evaluations.npz      # EvalCallback の評価履歴 (timesteps, results, ep_lengths)
        ├── learning_curve.png   # 報酬 vs step
        └── eval_metrics.json    # 最終評価 + プロベナンス情報
```

## クイックスタート

```bash
cd research-fields/mechanical-energy/02-rl-cartpole
python -m pip install -r requirements.txt

python src/train.py --timesteps 50000 --seed 42
python src/evaluate.py --model outputs/ppo_cartpole.zip --episodes 20
```

> **再現性重視の場合** — ハッシュ付きロックファイルを使う:
> ```bash
> # Linux + Python 3.12
> pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt
> ```
> macOS / Windows のロックファイルは `requirements-lock/` 内の手順で生成してください。

## タスク: CartPole-v1

- **状態** (4 次元): カート位置、カート速度、ポール角度、ポール角速度
- **行動** (2 択): 左に押す / 右に押す
- **報酬**: 各 step で +1 (ポールが ±12° 以内で立っている限り)
- **エピソード終了**: ポール角度 > ±12° or カート位置 > ±2.4 or 500 step 到達 (観測空間の上限は ±24°)
- **成功基準**: 100 エピソード平均リターン **≥ 475** (公式)

## スタック

| 種別 | 選定 | 理由 |
|---|---|---|
| 環境 | `gymnasium==1.3.*` | Gym の後継、公式メンテ |
| RL ライブラリ | `stable-baselines3==2.9.*` | 産業実績豊富、豊富なコールバック |
| アルゴリズム | PPO (MlpPolicy) | on-policy、安定して収束、ハイパラに寛容 |
| ベクトル化 | `SubprocVecEnv(4)` | CPU 4 コアで並列 rollout |

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [RL の考え方 (5 分)](docs/02-rl-concept.md) — 環境・行動・報酬・方策
3. [学習](docs/03-train.md) — CLI、コールバック、TensorBoard
4. [結果の読み方](docs/04-understand-results.md) — 学習曲線、評価
5. [別環境で試す](docs/05-other-envs.md) — MountainCar, LunarLander へ拡張
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md) — Sim-to-Real, 報酬設計の罠

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- `stable-baselines3`: MIT
- `gymnasium`: MIT
- CartPole 環境: OpenAI が Barto/Sutton の古典を実装したもの、Gymnasium が継承

## 免責

**本教材は RL 入門の最小例です。実物制御 (ロボット、産業機械、電力系統など) へは以下の追加検証が必須です:**
- Sim-to-Real gap の実測 (シミュ性能はしばしば実機で崩れる)
- 安全制約の hard constraint 化 (PPO は制約違反を確率的にしか避けない)
- 報酬関数のスペック外挙動 (reward hacking) の監査
