# 04 — 構造緩和の詳細

`src/relax.py` の内部動作とパラメータチューニングを解説します。

## パイプライン

```
[入力構造] → [MACE-MPA-0 calculator を割り当て]
   → [ExpCellFilter で全セル + 全原子を可変に]
   → [BFGS オプティマイザで F_max < 0.05 eV/Å まで反復]
   → [relaxed.extxyz / relaxed.cif / relax_metrics.json を保存]
```

## 主要な CLI オプション

| オプション | デフォルト | 意味 |
|---|---|---|
| `--system` | `Si` | プリセット結晶種 (Si / Ge / NaCl / Cu / Al / Fe) |
| `--input` | なし | 外部構造ファイル (CIF/extxyz/POSCAR)。指定時 `--system` を無視 |
| `--supercell NX NY NZ` | `1 1 1` | 単位胞の複製数 |
| `--model` | `medium-mpa-0` | MACE モデル名（MIT: `medium-mpa-0`, `medium`, `small`, `large`）|
| `--device` | `cpu` | `cpu` または `cuda` |
| `--dtype` | `float32` | `float32`（推奨）または `float64` |
| `--fmax` | `0.05` | 収束閾値 (eV/Å) |
| `--max-steps` | `300` | オプティマイザの最大反復数 |
| `--fix-cell` | オフ | セルを固定してイオン位置のみ緩和 |

## 全セル vs イオンのみ

- **既定 (全セル)**: `ExpCellFilter` で格子ベクトルも自由度に含める → 格子定数の予測ができる
- **`--fix-cell`**: 実験セルに固定してイオンのみ動かす → 表面吸着計算・欠陥導入時に使用

## モデル選択の指針

| モデル | 引数 | ライセンス | 精度 | 速度 |
|---|---|---|---|---|
| MACE-MPA-0 (**推奨**) | `--model medium-mpa-0` | **MIT** | 高 (MPtrj + sAlex) | 中 |
| MACE-MP-0a medium (レガシー) | `--model medium` | MIT | 中 | 中 |
| MACE-MP-0a small | `--model small` | MIT | 低 | 速 |
| MACE-MP-0a large | `--model large` | MIT | 最高 | 遅 |

**MACE-OMAT / MACE-MH / MATPES 系は ASL ライセンス（非商用）** で、教育・研究目的でも組織によっては使用不可な場合があります。本クイックスタートでは MIT モデルのみ推奨。

## 収束の目安 (Si ダイヤモンド、8 原子)

| 指標 | 目安 |
|---|---|
| 収束ステップ数 | < 30 (初期が実験格子に近い場合) |
| 最終 `F_max` | < 0.05 eV/Å |
| 最終 `E/atom` | 実行の再現性の目安 (dtype float32 なら ±1 meV 程度) |
| 緩和後格子定数 | 5.43〜5.47 Å (実験 5.431 Å + PBE 過大評価 ~0.5%) |

異常兆候:
- 300 ステップで収束しない → 初期構造が壊れている可能性大。`ase gui data/initial.extxyz` で確認
- エネルギーが数十 eV 以上ジャンプする → dtype 不整合、または NaN の発生（`torch.isnan` チェック）

## 自分の構造を試す

CIF / POSCAR / extxyz を `--input` で渡せます:

```bash
python src/relax.py --input my_zeolite.cif --fmax 0.02 --max-steps 500 --device auto
```

**元素カバレッジ**: MACE-MPA-0 は Materials Project 上でトラジェクトリが十分に存在する主要元素セットを学習しています。厳密な対応リストとチェック方法は [07-ethics-and-limits.md § 2 元素・化学環境のカバレッジ](07-ethics-and-limits.md#2-元素化学環境のカバレッジ) を参照。範囲外の元素を投入すると `src/relax.py` は `--allow-elements-outside-domain` を要求して停止します。

## パラメータ調整 tips

- **収束が遅い**: `--max-steps 500` に増やす、または初期構造を確認
- **格子が急に大きくなる**: 目標系の空間群に応じて `ase.constraints.FixSymmetry` を使う（本スクリプトでは非対応、必要なら手動追加）
- **金属系の緩和**: 磁性を扱わないため、Fe/Ni/Co 系は誤差が大きい可能性
- **高圧計算**: `ExpCellFilter(atoms, scalar_pressure=pressure_GPa * ase.units.GPa)` で圧力を印加できます。**必ず `ase.units.GPa` をかけて eV/Å³ 単位に変換してください**。生の GPa 数値をそのまま渡すと 1 GPa のつもりが 160 GPa 相当の圧力になってしまいます（ASE の内部単位が eV/Å³ で、1 eV/Å³ ≈ 160 GPa のため）

## 出力ファイルの読み方

**`relax_metrics.json`** の例:
```json
{
  "source": "preset:Si(diamond,a=5.431)",
  "n_atoms": 8,
  "final_energy_eV": -34.8235,
  "final_energy_per_atom_eV": -4.3529,
  "final_fmax_eV_per_Ang": 0.0009,
  "n_steps": 3,
  "converged": true,
  "final_cell_Ang": [[5.4312, 0, 0], [0, 5.4312, 0], [0, 0, 5.4312]],
  "final_volume_Ang3": 160.243
}
```

**`relaxation.traj`** は ASE トラジェクトリ形式:
```python
from ase.io.trajectory import Trajectory
for i, atoms in enumerate(Trajectory("data/relaxation.traj")):
    print(i, atoms.get_potential_energy())
```
