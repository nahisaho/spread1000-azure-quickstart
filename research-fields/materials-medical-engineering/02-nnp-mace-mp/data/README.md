# data/ ディレクトリ

このディレクトリは実行時に自動生成されるファイルの置き場所です。**リポジトリには何も含めていません**（`.gitignore` 済み）。

## 生成されるファイル

| ファイル | 生成元 | 内容 |
|---|---|---|
| `initial.extxyz` | `src/build_structure.py` | 初期構造 (ASE `bulk()` で構築) |
| `relaxed.extxyz` | `src/relax.py` | 緩和後の最終構造 |
| `relaxation.traj` | `src/relax.py` | BFGS 各ステップのトラジェクトリ |
| `relaxation.log` | `src/relax.py` | ASE optimizer のログ |
| `relax_metrics.json` | `src/relax.py` | 最終エネルギー・F_max・格子定数など |
| `md.traj` | `src/run_md.py` | MD トラジェクトリ (10 ステップごとに保存) |
| `md_metrics.json` | `src/run_md.py` | 平均温度・エネルギー統計 |

## 可視化

- **VESTA** ( https://jp-minerals.org/vesta/en/ ) — `relaxed.extxyz` を CIF に変換して開く
- **Ovito** ( https://www.ovito.org/ ) — `.extxyz` / `.traj` を直接読める
- **ASE GUI** — `ase gui data/relaxation.traj`

## クリーンアップ

```bash
rm -rf data/*.traj data/*.extxyz data/*.log data/*.json
```
