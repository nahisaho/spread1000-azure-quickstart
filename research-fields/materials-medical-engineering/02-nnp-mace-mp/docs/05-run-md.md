# 05 — Langevin NVT-MD の詳細

`src/run_md.py` の内部動作とパラメータチューニングを解説します。

## パイプライン

```
[緩和済み構造] → [MACE-MPA-0 calculator を割り当て]
   → [MaxwellBoltzmannDistribution で初速度を目標温度に設定]
   → [Langevin thermostat (NVT) で 5 ps 実行 (dt=1 fs)]
   → [10 ステップごとに md.traj に保存, 温度/エネルギーを記録]
   → [md.traj / md_metrics.json を保存]
```

## 主要な CLI オプション

| オプション | デフォルト | 意味 |
|---|---|---|
| `--input` | `data/relaxed.extxyz` | 初期構造 (通常は緩和後のもの) |
| `--temperature` | `300.0` | 目標温度 (K) |
| `--timestep-fs` | `1.0` | MD 時間刻み (fs)。1 fs は軽元素系で無難 |
| `--friction-inv-fs` | `0.01` | Langevin 摩擦係数 (1/fs)。大きくすると温度追随が速くなり保存量が壊れる |
| `--steps` | `5000` | 総ステップ数（dt=1 fs なら 5000 = 5 ps） |
| `--save-every` | `10` | トラジェクトリ保存間隔 |
| `--seed` | `42` | 初速度乱数シード |

## 各パラメータの選び方

### タイムステップ (`--timestep-fs`)

| 系 | 推奨 dt |
|---|---:|
| 水素含有系 (H, D) | 0.5 fs |
| Si, Ge, C など軽〜中程度 | 1.0 fs (既定) |
| Cu, Au, Pt など重元素のみ | 1.0〜2.0 fs |

**dt を大きくしすぎると** エネルギー保存則が破れ、Langevin の温度制御でも系が発散します。

### 摩擦係数 (`--friction-inv-fs`)

- `0.001〜0.01` : 弱結合。系のダイナミクスに近い（NVE 的）
- `0.01` : 既定。温度平衡までに数百 fs かかるが動力学的性質はほぼ保たれる
- `0.1` : 強結合。温度は素早く目標に達するが動力学が壊れる

**構造探索** には既定値、**輸送特性の計算** は `0.001` 以下を推奨。

### 系のサイズ

- 8 原子 Si (単位胞) : 温度ゆらぎが ±60 K 程度と大きい
- 32 原子 (2×1×1) : ±30 K 程度
- 64 原子 (2×2×2) : ±20 K 程度

**熱平衡値** を得たい場合は最低でも 64 原子以上を推奨。

## 実行例

### 基本 (既定)
```bash
python src/run_md.py --input data/relaxed.extxyz --steps 5000
```

### 高温 (1000 K, 焼きなましのイメージ)
```bash
python src/run_md.py --input data/relaxed.extxyz --temperature 1000 --steps 10000
```

### 大きな系で長時間
```bash
python src/run_md.py --input data/big_supercell.extxyz \
  --temperature 500 --steps 50000 --device cuda --dtype float32
```

## 出力ファイル

**`md_metrics.json`** の例:
```json
{
  "input": "data/relaxed.extxyz",
  "n_atoms": 8,
  "temperature_target_K": 300.0,
  "timestep_fs": 1.0,
  "n_steps": 5000,
  "total_time_ps": 5.0,
  "n_frames_saved": 500,
  "temperature_mean_K": 302.4,
  "temperature_std_K": 45.1,
  "e_pot_mean_eV": -34.812,
  "e_pot_std_eV": 0.104
}
```

**`md.traj`** は Ovito / VMD / ASE GUI で開けます:
```bash
ovito data/md.traj
# または
ase gui data/md.traj
```

Python で温度履歴プロット:
```python
from ase.io.trajectory import Trajectory
import numpy as np, matplotlib.pyplot as plt

traj = Trajectory("data/md.traj")
temps = [a.get_temperature() for a in traj]  # (3N-3) DoF を考慮
plt.plot(np.arange(len(temps)) * 10, temps)  # save_every=10
plt.xlabel("MD step"); plt.ylabel("T (K)")
plt.axhline(300, color="k", ls="--", alpha=0.5)
plt.tight_layout(); plt.savefig("data/md_temperature.png", dpi=120)
```

## トラブル

| 症状 | 原因 | 対処 |
|---|---|---|
| `⟨T⟩` が目標から 100 K 以上ずれる | `--steps` が少なすぎ (平衡到達前) | `--steps 10000` に増やす、または `--friction-inv-fs 0.05` に |
| ポテンシャルエネルギーが発散 | dt が大きすぎる、水素系で 0.5 fs 未満必須 | `--timestep-fs 0.5` に |
| メモリ不足 (CPU) | 系が大きすぎ | `--supercell` を小さく、または `--device cuda` |

## 次のステップ

大規模化・生産計算に進む場合は、LAMMPS + `pair_style mace` の使用を検討してください（本クイックスタートでは範囲外）。参考: https://mace-docs.readthedocs.io/en/latest/guide/lammps.html
