# data/ ディレクトリ

このディレクトリは実行時に自動生成されるファイルの置き場所です。**リポジトリには何も含めていません**（`.gitignore` 済み）。

## 生成されるファイル

| ファイル | 生成元 | 内容 |
|---|---|---|
| `initial.extxyz` | `src/build_structure.py` | 初期構造 (ASE `bulk()` で構築) |
| `relaxed.extxyz` | `src/relax.py` | 緩和後の最終構造 (extxyz) |
| `relaxed.cif` | `src/relax.py` | 緩和後の最終構造 (VESTA 用 CIF) |
| `relaxation.traj` | `src/relax.py` | BFGS 各ステップのトラジェクトリ |
| `relaxation.log` | `src/relax.py` | ASE optimizer のログ |
| `relax_metrics.json` | `src/relax.py` | 最終エネルギー・F_max・格子定数・応力・再現性メタ |
| `md.traj` | `src/run_md.py` | MD トラジェクトリ (equilibration 後のみ、`--save-every` ごとに保存) |
| `md_metrics.json` | `src/run_md.py` | 平均温度・エネルギー統計・NaN チェック結果・再現性メタ |
| `*.png` | 可視化コード (`docs/02-cpu-quickstart.md`) | エネルギー履歴・温度履歴プロット (opt-in) |

## 可視化

- **VESTA** ( https://jp-minerals.org/vesta/en/ ) — `relaxed.cif` を直接開ける
- **Ovito** ( https://www.ovito.org/ ) — `.extxyz` / `.traj` を直接読める
- **ASE GUI** — `ase gui data/relaxation.traj`

## クリーンアップ

```bash
rm -rf data/*.traj data/*.extxyz data/*.cif data/*.log data/*.json data/*.png
```

