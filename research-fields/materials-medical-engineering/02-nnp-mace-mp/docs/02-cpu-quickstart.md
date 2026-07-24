# 02 — CPU / WSL2 クイックスタート

Azure を使わず、手元のマシンだけで MACE-MP-0 の全体像を体験します。8 原子の Si ダイヤモンドなら、CPU でも 5〜10 分で構造緩和 + 短時間 MD が完結します。

## 前提

[01-prerequisites.md](01-prerequisites.md) の手順で以下が完了していること:
- Python 3.10〜3.12 の仮想環境（`.venv`）が有効
- `torch==2.4.0` (CPU 版) と mace-torch がインストール済み
- `mace_mp(model='medium-mpa-0', device='cpu')` が "OK" を返すことを確認

## Step 1: 初期構造の生成（任意）

`src/relax.py` は `--system Si` を指定するだけで内部で構造を作りますが、CIF 出力を確認したい場合は `build_structure.py` を単体で実行できます:

```bash
python src/build_structure.py --system Si --supercell 1 1 1 --output data/initial.extxyz
```

**出力**:
```
[build] Si diamond a=5.431 Å
[build] supercell 1×1×1 → 8 atoms
[build] wrote data/initial.extxyz
```

利用可能なプリセット: `Si`, `Ge`, `NaCl`, `Cu`, `Al`, `Fe`。他は `--input my_structure.cif` を使ってください。

## Step 2: 構造緩和（BFGS + 全セル + イオン）

```bash
# --device auto は CPU / CUDA を自動判定。CPU 固定なら --device cpu を明示。
python src/relax.py --system Si --supercell 1 1 1 --device auto --dtype float32 --output data/
```

**期待される出力**:
```
[relax] source: preset:Si(diamond,a=5.431)
[relax] atoms: 8 (Si8)
[relax] device=cpu dtype=float32 model=medium-mpa-0
[relax] loading MACE calculator (first run downloads ~80 MB) ...
[relax] initial E = -34.82 eV  (-4.353 eV/atom), F_max = 0.0032 eV/Å
       Step     Time          Energy          fmax
BFGS:    0   ...        -34.8215       0.0032
BFGS:    1   ...        -34.8215       0.0028
...
[relax] ✅ CONVERGED: E = -34.82 eV (-4.353 eV/atom)
[relax]   F_max = 0.0009 eV/Å in 3 steps
[relax]   volume = 160.243 Å³
[relax] wrote data/relaxed.extxyz, relaxed.cif, relax_metrics.json
```

> 💡 Si は実験格子定数 5.431 Å で既にほぼ緩和済みなので数ステップで収束します。**初期構造を歪ませたい**なら supercell を大きくして、格子定数を意図的にずらしてください:
> ```bash
> python src/build_structure.py --system Si --supercell 2 2 2 --output data/initial.extxyz
> # 続けて data/initial.extxyz を --input に渡し歪みを付与する
> ```

## Step 3: 5 ps NVT MD (fixed-cell Langevin, 300 K)

```bash
# --equilibration-steps 1000 : 最初の 1000 step は熱化中扱いとして md.traj に含めない
python src/run_md.py --input data/relaxed.extxyz --steps 5000 --equilibration-steps 1000 \
  --temperature 300 --device auto --dtype float32
```

**期待される出力**:
```
[md] loaded 8 atoms (Si8) from data/relaxed.extxyz
[md] loading MACE calculator ...
[md] step    200 (  0.20 ps) T= 285.3 K  E_pot=-34.7912  E_kin=0.1096
[md] step    400 (  0.40 ps) T= 312.7 K  E_pot=-34.7823  E_kin=0.1201
...
[md] wrote data/md.traj (401 frames after equilibration), md_metrics.json
[md] ⟨T⟩ = 302.4 ± 45.1 K (target 300 K, equilibration steps discarded)
```

> ⚠️ **本 quickstart の `run_md.py` は fixed-cell NVT**（セル固定・Langevin thermostat）です。液体・ソフトマターの熱膨張や NPT 計算には向きません。
>
> Langevin の摩擦係数は温度追従を改善する反面、**動力学的性質 (拡散係数・振動スペクトル・粘性など) を歪めます**。物性計算には既定の弱結合 (`--friction-inv-fs 0.01`) を維持し、統計量には十分な系サイズと時間を確保してください。

## Step 4: fail-fast 検証

```bash
python src/verify.py --relax data/relax_metrics.json --md data/md_metrics.json \
  --expected-lattice-a-Ang 5.43
```

`verify.py` は relax/MD の metrics.json を読み、有限性 (NaN/Inf)、収束、格子定数許容範囲、応力許容範囲、温度追従、平均ポテンシャル/atom のドリフト、再現性メタ (mace/torch/CUDA/git commit/model SHA-256) の存在まで exit code で判定します。合格 = `exit 0`。

## Step 4: 結果の可視化

**Ovito** で MD を再生:
```bash
ovito data/md.traj
```

**VESTA** で緩和後結晶を表示:
```bash
vesta data/relaxed.cif
```

**Python でパリティプロット**（緩和トラジェクトリのエネルギー履歴）:
```python
from ase.io.trajectory import Trajectory
import matplotlib.pyplot as plt

traj = Trajectory("data/relaxation.traj")
energies = [a.get_potential_energy() for a in traj]
plt.plot(energies, "o-")
plt.xlabel("BFGS step"); plt.ylabel("Energy (eV)")
plt.tight_layout(); plt.savefig("data/relax_energy.png", dpi=120)
```

生成した `data/*.png` は `.gitignore` 済みなので、[06-cleanup.md](06-cleanup.md) に従って一括削除できます。

## 実行時間の目安（CPU, 4 コア、8 原子 Si）

| ステップ | 時間 |
|---|---:|
| 初回のモデルダウンロード | 30 秒〜3 分（ネットワーク次第） |
| 静的エネルギー・力の計算 | < 1 秒 |
| 構造緩和 (BFGS, 10 ステップ) | 5〜20 秒 |
| MD 5000 ステップ (5 ps) | 3〜8 分 |

**32 原子（`--supercell 2 1 1`）に増やすと MD は 10〜25 分**。ローカル CPU での上限はこの規模です。

## 次のステップ

- 自分の構造を試したい → `src/relax.py --input my_material.cif`
- GPU で高速化したい → [03-aml-gpu.md](03-aml-gpu.md) (Azure ML)
- 詳細なパラメータ調整 → [04-run-relaxation.md](04-run-relaxation.md)
