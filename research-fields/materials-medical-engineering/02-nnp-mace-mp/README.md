# 02 — MACE-MP-0 汎用 NNP による構造緩和・分子動力学

**MACE-MPA-0**（Foundation Model NNP、MIT ライセンス）を使い、Si ダイヤモンド結晶の構造緩和と短時間 MD を実行します。

> **⚡ 最短パス（推奨）**: **CPU / WSL2 / ローカル Python で完結、Azure 課金 0 円。**8 原子 Si の緩和は約 1 分、5 ps MD は数分で終わります。
>
> Azure ML GPU (T4) を使いたい場合の追加手順は [docs/03-aml-gpu.md](docs/03-aml-gpu.md) を参照（$0.5〜1、GPU クォータ申請が必要）。

## SPReAD-1000 対応課題

材料・応用医工学分野で **NNP / MD / 第一原理計算代替** を扱う課題向け。同じ手順で任意の CIF や `ase.io.read()` 可能な構造に適用できます。

## 使う技術

| コンポーネント | 用途 | ライセンス |
|---|---|---|
| **MACE-MPA-0** (`mace-torch>=0.3.16`) | 汎用 NNP 基盤モデル（89 元素対応） | MIT |
| ASE (`ase`) | 構造構築・オプティマイザ・MD ドライバ | LGPL |
| PyTorch **2.4.0** | NNP 実行 | BSD |

**引用**: Batatia et al., *A foundation model for atomistic materials chemistry*, arXiv:2401.00096 (2023). JCP 163, 184110.

## クイックスタート (CPU / ローカル)

```bash
# 1. Python 3.10〜3.12 の仮想環境を作る（3.13 は未対応）
python3.12 -m venv .venv
source .venv/bin/activate

# 2. PyTorch 2.4.0 を先に固定インストール（重要）
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cpu

# 3. mace-torch とその他
pip install -r requirements.txt

# 4. Si ダイヤモンド 8 原子の構造緩和
python src/relax.py --system Si --supercell 1 1 1 --output data/

# 5. 5 ps NVT-MD（Langevin, 300 K）
python src/run_md.py --input data/relaxed.extxyz --output data/ --steps 5000
```

**期待される出力**:
- `data/relaxed.extxyz` — 緩和後構造 (Ovito/VESTA で表示可能)
- `data/relaxation.traj` — ASE トラジェクトリ
- `data/relax_metrics.json` — 最終エネルギー・F_max・格子定数
- `data/md.traj` — MD トラジェクトリ
- `data/md_metrics.json` — 温度・エネルギーの統計

**成功基準 (Si ダイヤモンド)**:
- `F_max < 0.05 eV/Å` （BFGS 収束）
- 緩和後の格子定数 5.43〜5.47 Å (実験値 5.431 Å の DFT-PBE 近傍)
- 収束ステップ数 < 100

## ディレクトリ構成

```
02-nnp-mace-mp/
├── README.md            # 本ファイル
├── troubleshooting.md   # よくあるトラブル
├── requirements.txt     # pip 依存 (torch は別途インストール)
├── src/
│   ├── build_structure.py  # ASE bulk() で構造構築
│   ├── relax.py            # BFGS + ExpCellFilter 構造緩和
│   └── run_md.py           # Langevin NVT MD
├── data/                # 生成物 (gitignore、実行時に作成)
└── docs/
    ├── 01-prerequisites.md  # Python/PyTorch 依存の詳細
    ├── 02-cpu-quickstart.md # CPU/WSL2 実行手順
    ├── 03-aml-gpu.md        # Azure ML GPU の追加手順 (任意)
    ├── 04-run-relaxation.md # 構造緩和の詳細
    ├── 05-run-md.md         # MD 実行の詳細
    ├── 06-cleanup.md        # 後片付け
    └── 07-ethics-and-limits.md  # ライセンス・DFT の限界
```

## コスト目安

| 実行環境 | 8 原子 Si フル実行時間 | コスト |
|---|---:|---:|
| **ローカル / WSL2 (CPU)** | 5〜10 分 | **$0** |
| Azure ML CI (`NC4as_T4_v3`, PAYG) | 30 分 (セットアップ込み) | ~$0.50 |
| Azure ML CI (`NC4as_T4_v3`, Spot) | 30 分 | ~$0.22 |

## 参考文献

- Batatia et al., *A foundation model for atomistic materials chemistry*, arXiv:2401.00096 (2023) — MACE-MP-0 論文
- MACE-Foundations GitHub: https://github.com/ACEsuit/mace-foundations
- mace-docs: https://mace-docs.readthedocs.io/
- 詳細な引用と制限事項は [docs/07-ethics-and-limits.md](docs/07-ethics-and-limits.md)
