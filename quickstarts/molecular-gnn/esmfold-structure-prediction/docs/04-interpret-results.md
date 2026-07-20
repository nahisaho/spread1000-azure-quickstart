# 04 — 結果の解釈（PDB, pLDDT）

所要 15 分。ここでは推論結果の見方、可視化、次のアクションを説明します。

## ⚠️ 予測構造は「仮説」です

ESMFold の出力は **AI による予測** であり、実験構造ではありません。以下を必ず理解してください。

- **論文発表・特許出願の前に必ず実験検証**（X 線、CryoEM、NMR、機能アッセイ）を組み合わせる
- **pLDDT が低い領域（<70）は信頼できない** — 無秩序領域（IDR）または低精度
- **タンパク質–タンパク質界面や多量体は予測しない**（単鎖のみ）
- **点変異の効果予測は苦手** — 野生型に近い予測を返しやすい
- **触媒残基・活性中心の細かな配置** はケースバイケースで検証が必要

## 1. pLDDT スコアの読み方

pLDDT (predicted Local Distance Difference Test) は 0〜100 の残基ごとの信頼度スコアです。**AlphaFold2 と同じスケール**です。

| pLDDT | 信頼度 | 標準色 | 解釈 |
|---|---|---|---|
| **90–100** | Very high | 濃青 | バックボーンは高信頼、側鎖もそこそこ信頼できる。**実験構造の代替ではない** |
| **70–89** | High | 水色 | バックボーンは信頼、側鎖は要注意 |
| **50–69** | Low | 黄色 | 折りたたみの傾向のみ、位置は不確か |
| **< 50** | Very low | 橙 | **無秩序領域（IDR）または誤予測** |

### PDB ファイル内の pLDDT

PDB ファイルの各 ATOM 行の **B-factor（temperature factor）列** に pLDDT が格納されています：

```
ATOM   1015  CA  GLY A 134     ...  1.00 96.14  C
                                          ^^^^^ ← pLDDT = 96.14
```

PyMOL や ChimeraX、py3Dmol は B-factor によるカラーリング（**AlphaFold カラー**）に対応しています。

### CSV での per-residue pLDDT

`run-inference.py --output` で生成される `<seq_id>_plddt.csv`：

```csv
residue_index,residue,plddt
1,M,72.5
2,Q,89.1
3,I,94.8
...
```

## 2. py3Dmol で Jupyter 上に可視化

```python
import py3Dmol

with open("output/ubiquitin.pdb") as f:
    pdb_str = f.read()

view = py3Dmol.view(width=600, height=500)
view.addModel(pdb_str, "pdb")

# AlphaFold カラーリング (pLDDT による色分け)
view.setStyle({}, {"cartoon": {"colorscheme": {
    "prop": "b",
    "gradient": "roygb",
    "min": 50,
    "max": 90
}}})
view.zoomTo()
view.show()
```

**pLDDT の分布ヒストグラム**：

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

df = pd.read_csv("output/ubiquitin_plddt.csv")
plt.figure(figsize=(10, 4))
plt.subplot(1, 2, 1)
plt.plot(df["residue_index"], df["plddt"], color="C0")
plt.axhline(70, color="orange", linestyle="--", label="pLDDT=70")
plt.axhline(90, color="blue", linestyle="--", label="pLDDT=90")
plt.xlabel("Residue")
plt.ylabel("pLDDT")
plt.legend()
plt.subplot(1, 2, 2)
plt.hist(df["plddt"], bins=20, color="C2", edgecolor="black")
plt.xlabel("pLDDT")
plt.ylabel("# residues")
plt.tight_layout()
plt.savefig("output/ubiquitin_plddt.png", dpi=150)
```

## 3. pTM スコア（全体信頼度）

`run-inference.py --summary` で出力される `ptm` は 0〜1 の全体構造 TM-score の **予測値** です（実測 TM-score とは別物）。

| pTM | 解釈 |
|---|---|
| **> 0.8** | 全体トポロジーの予測に高い自信 |
| **0.5–0.8** | 折りたたみの型については中程度の自信 |
| **< 0.5** | モデルが全体構造に自信を持てなかったことを示す。**新規折りたたみを支持する証拠にはならない**（無秩序、柔軟なマルチドメイン、単なる予測失敗など複数の原因があり得る） |

> [!IMPORTANT]
> pTM は **信頼度指標** です。低い pTM が「新規折りたたみを発見した」の根拠にはなりません。新規性の主張には Foldseek 等での既存構造との比較と実験検証が不可欠です。

## 4. 既知の構造と比較（重要）

予測構造の**妥当性検証**には既知構造との比較が有効です：

```bash
# TM-align で既知 PDB (例: 1UBQ) と比較
# TM-align は http://zhanggroup.org/TM-align/ からダウンロード可
./TMalign output/ubiquitin.pdb 1ubq.pdb
```

出力の `TM-score` が **> 0.5** なら同一折りたたみ、**> 0.9** なら実験構造とほぼ同一。

### 既存 PDB エントリ検索

```python
# ホモロジー検索（Foldseek 推奨、AF-DB や PDB 全体を秒単位で検索）
# https://search.foldseek.com/search
# アップロード: output/ubiquitin.pdb
```

## 5. batch 推論結果の要約

`--summary summary.csv` を指定すると以下の CSV が出力されます：

```csv
seq_id,length,mean_plddt,ptm,inference_sec
ubiquitin,76,93.4,0.89,8.2
lysozyme,129,88.7,0.82,15.4
insulin,51,85.2,0.71,4.8
...
```

推奨フィルタリング（下流解析に使う配列を絞る）：

```python
import pandas as pd
df = pd.read_csv("output/batch/summary.csv")

# 全体信頼度で絞り込み
high_quality = df[(df["mean_plddt"] > 70) & (df["ptm"] > 0.7)]
print(f"{len(high_quality)} / {len(df)} passed quality filter")
```

## 6. 次のステップ（研究者向け）

| 目的 | 推奨ツール |
|---|---|
| **触媒残基・結合部位予測** | PrankWeb, P2Rank |
| **リガンド ドッキング** | AutoDock Vina, DiffDock |
| **既知構造との類似性検索** | Foldseek |
| **タンパク質–タンパク質複合体予測** | AlphaFold-Multimer, AlphaFold3（別クイックスタート予定） |
| **分子動力学（MD）シミュレーション** | GROMACS, OpenMM（次期 GPU 系クイックスタート予定） |

## 完了チェック

- [ ] `output/*.pdb` を PyMOL または py3Dmol で開き、AlphaFold カラーで表示できる
- [ ] `<seq_id>_plddt.csv` で残基ごとの pLDDT を確認できる
- [ ] mean pLDDT と pTM の意味と閾値を理解した
- [ ] **予測構造は仮説であり実験検証が必須** であることを理解した

**次**: [05-cleanup.md](05-cleanup.md) — 課金停止手順
