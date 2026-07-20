# 04 — 生成結果を読み解く

所要 10 分。ここでは `output/<pdb>/` に生成された分子（SMILES + 物性）をどう読むかを説明します。

## 生成結果の位置づけ

> [!IMPORTANT]
> **TamGen の出力は「計算による分子生成の仮説」です。** 以下のいずれも実験・専門家評価を経ておらず、そのままで意思決定に使ってはいけません。
>
> - **標的への結合親和性は保証されません**（生成分子は「結合しそう」に見える構造で、実測値はゼロ）。
> - **合成可能性は評価されていません**（SYBA/SAScore など別途スコアリング必須）。
> - **毒性・薬物動態・規制物質該当性は評価されていません**（[README.md 責任ある AI 利用](../README.md#責任ある-ai-利用) 参照）。
> - **有効な SMILES の割合は 100 % ではありません**（1〜5 % 程度は化学的に無効）。
>
> 生成結果は必ずドッキング・ADMET 予測・医薬品化学者レビュー・実験的検証をこの順で経てください。

## 出力ファイルの構成

`run-inference.sh 3wze` を実行すると、以下が生成されます。

```
~/TamGen/output/3wze/
├── generated_molecules.csv     # SMILES + 物性 (下表)
├── generated_molecules.smi     # SMILES のみ (1 行 1 分子)
└── generation_stats.json       # 生成統計
```

`generated_molecules.csv` の列（本クイックスタートの [`generate_from_pdb.py`](../scripts/generate_from_pdb.py) が RDKit で計算）：

| 列名 | 意味 | 目安 |
|---|---|---|
| `SMILES` | 生成分子の構造 | — |
| `MW` | 分子量 (g/mol) | Lipinski 適合 ≤ 500 |
| `LogP` | オクタノール／水分配係数 | Lipinski 適合 ≤ 5 |
| `QED` | Drug-likeness スコア (0-1) | 高いほど医薬品らしい。0.5 以上が目安 |
| `TPSA` | 極性表面積 (Å²) | 経口薬候補は 20-140 |
| `HBD` / `HBA` | 水素結合ドナー／アクセプター数 | Lipinski: HBD≤5, HBA≤10 |
| `NumRings` | 環数 | 3〜4 が典型 |
| `Lipinski` | ルール適合 (True/False) | 経口医薬品候補フィルタ |

> [!NOTE]
> **上流 `example_inference.sh` の出力とは異なります。** 上流は `test_id, smiles, nlogP`（生成スコア）の 3 列のみを出力します。本クイックスタートは実用性のため独自にポストプロセスしています。

## クイックに絞り込む

Compute Instance のターミナル（`conda activate TamGen`）で、Python REPL または新規 Notebook セル：

```python
import pandas as pd
df = pd.read_csv("output/3wze/generated_molecules.csv")
print(f"生成分子数: {len(df)}")
print(f"Lipinski 適合: {df['Lipinski'].sum()} 件")

# 医薬品らしさ上位 20
top = df[df['Lipinski']].sort_values('QED', ascending=False).head(20)
print(top[['SMILES', 'MW', 'LogP', 'QED']])
top.to_csv("output/3wze/top20_druglike.csv", index=False)
```

## RDKit で構造を描画（Notebook 上）

```python
from rdkit import Chem
from rdkit.Chem import Draw

mols = [Chem.MolFromSmiles(s) for s in top['SMILES'].tolist()[:12]]
mols = [m for m in mols if m is not None]
Draw.MolsToGridImage(
    mols, molsPerRow=4, subImgSize=(220, 220),
    legends=[f"QED={q:.2f}" for q in top['QED'].tolist()[:len(mols)]],
)
```

## 次のアクション

- **ドッキング検証**: 生成分子を AutoDock Vina / DiffDock で標的タンパク質に in silico ドッキングし、結合エネルギーで並べ替え
- **ADMET 予測**: [ADMET-AI](https://github.com/swansonk14/admet_ai)（Stanford, OSS）や商用ツールで毒性・薬物動態を絞り込み
- **合成可能性**: SYBA / SAScore 等でスコアリングし、合成容易な候補に絞り込み
- **医薬品化学レビュー**: 熟練の医薬品化学者による目視スクリーニング（PAINS / reactive group チェック等）
- **実験フィードバック**: ウェット試験結果を教師データにファインチューニング（TamGen の学習スクリプト `scripts/train.sh` が使えます）

## 引用

論文を引用する場合の BibTeX：

```bibtex
@article{Wu2024TamGen,
  author  = {Wu, Kehan and Xia, Yingce and Deng, Pan and Liu, Renhe
             and Zhang, Yuan and Guo, Han and Cui, Yumeng and Pei, Qizhi
             and Wu, Lijun and Xie, Shufang and Chen, Si and Lu, Xi
             and Hu, Song and Wu, Jinzhi and Chan, Chi-Kin and Chen, Shawn
             and Zhou, Liangliang and Yu, Nenghai and Chen, Enhong
             and Liu, Haiguang and Guo, Jinjiang and Qin, Tao
             and Liu, Tie-Yan},
  title   = {TamGen: drug design with target-aware molecule generation through
             a chemical language model},
  journal = {Nature Communications},
  volume  = {15},
  pages   = {9360},
  year    = {2024},
  doi     = {10.1038/s41467-024-53632-4}
}
```

**次**: [05-cleanup.md](05-cleanup.md) — 後始末（コスト対策）

