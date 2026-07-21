# 04 — 結果の解釈（mmCIF, pLDDT, pTM, ipTM, ranking score）

所要 20 分。ここでは AF3 の出力ファイル構造、各信頼度スコアの意味、
可視化、そして注意すべき解釈上の落とし穴を解説します。

## ⚠️ 予測構造は「仮説」です

AF3 の出力は **AI による予測** であり、実験構造ではありません。以下を必ず理解してください。

- **論文発表・特許出願の前に必ず実験検証**（X 線、CryoEM、NMR、機能アッセイ、SPR など）を組み合わせる
- **pLDDT が低い領域 (<70) は信頼できない** — 無秩序領域 (IDR) または低精度
- **リガンド結合姿勢は特に予測誤差が大きい** — 化学的妥当性 (chirality, valence, clash) を手動でチェック
- **触媒残基・活性中心の細かな配置** はケースバイケースで検証が必要
- **タンパク質-核酸複合体は依然として難しいターゲット** — ipTM が高くても実験で覆るケースあり
- **医療・臨床判断や創薬の意思決定には利用しない**

出力に含まれる `TERMS_OF_USE.md` を **削除せずに保持** してください。
これが AF3 Output Terms of Use による帰属表示要件を満たします。

## 1. 出力ファイル構造

`run-inference.py` が完了すると、次の構造で出力されます:

```text
/mnt/af3/outputs/<job_name>/
├── <job_name>_model.cif                              ← トップランクの構造（mmCIF）
├── <job_name>_confidences.json                       ← 詳細な信頼度（残基/原子ペアの PAE 等）
├── <job_name>_summary_confidences.json               ← サマリ (トップランク: ptm, iptm, ranking_score, fraction_disordered, has_clash)
├── <job_name>_data.json                              ← 拡張入力（MSA + テンプレート情報）
├── <job_name>_ranking_scores.csv                     ← 全サンプルのランキング
├── TERMS_OF_USE.md                                   ← 出力ライセンス（削除しない）
├── <job_name>_seed-42_sample-0_model.cif             ← 各サンプル (既定 5 サンプル)
├── <job_name>_seed-42_sample-0_confidences.json
├── <job_name>_seed-42_sample-0_summary_confidences.json
├── <job_name>_seed-42_sample-1_model.cif
...
└── <job_name>_seed-42_sample-4_summary_confidences.json
```

> [!IMPORTANT]
> AF3 は **PDB ではなく mmCIF** を出力します。PDB 形式に変換する場合は
> `gemmi convert model.cif model.pdb` を使えますが、AF3 は modified residues や
> 二文字元素のリガンド原子など PDB フォーマット上限を超える情報を含み得るため、
> **可能な限り mmCIF のまま解析**することを推奨します。

## 2. pLDDT スコア

pLDDT (predicted Local Distance Difference Test) は **0〜100 の per-atom 信頼度**です。
AlphaFold 2 が per-residue だったのに対し、**AF3 は per-atom** に変わっています（リガンド原子等を含むため）。

| pLDDT | 信頼度 | 標準色 | 解釈 |
|---|---|---|---|
| **90–100** | Very high | 濃青 | バックボーン/原子位置とも高信頼 |
| **70–89** | High | 水色 | バックボーンは信頼、側鎖は要注意 |
| **50–69** | Low | 黄色 | 折りたたみの傾向のみ、位置は不確か |
| **< 50** | Very low | 橙 | **無秩序領域または誤予測** |

### mmCIF ファイル内の pLDDT

mmCIF の `_atom_site.B_iso_or_equiv` 列（ChimeraX / PyMOL 表示上は「B-factor」）に pLDDT が格納されています：

```
ATOM 1 N N . MET A 1 1 ? 12.345 6.789 -1.234 1.00 96.14 ? 1 MET A N 1
                                                        ^^^^^ ← pLDDT = 96.14
```

ChimeraX / PyMOL / Mol* は B-factor によるカラーリング（**AlphaFold カラー**）に対応しています。

## 3. pTM と ipTM（全体信頼度）

`<job>_summary_confidences.json` 内の `ptm` および `iptm` は **0〜1** の値です。

| スコア | 意味 |
|--------|------|
| `ptm` | 全体構造トポロジーの予測 TM-score |
| `iptm` | **鎖間の相対配置**（インターフェース）の TM-score 予測 |

### 解釈の目安（DeepMind 公式）

| ipTM | 解釈 |
|------|------|
| **> 0.8** | 高品質・自信あり |
| **0.6–0.8** | グレーゾーン、追加検証必要 |
| **< 0.6** | おそらく失敗 |

| pTM | 解釈 |
|-----|------|
| **> 0.8** | 全体トポロジーに高い自信 |
| **0.5–0.8** | 折りたたみの型については中程度の自信 |
| **< 0.5** | モデルが全体構造に自信を持てなかった |

> [!IMPORTANT]
> **単体タンパク質 (monomer) では ipTM を鎖内局所信頼度として解釈しないでください**。
> ipTM は本来「複数エンティティ間の相対配置」の指標です。単体でも数値は出ますが意味は限定的。
> 単体タンパクでは **pLDDT (per-atom) と pTM (global)** を主に見てください。

> [!IMPORTANT]
> **短鎖 (<50 aa) は TM-score が原理的に厳しく評価されるため、pTM が低く出やすい**です。
> 短鎖ペプチドの pTM=0.4 だからといって予測失敗とは限りません。pLDDT を優先してください。

## 4. ranking_score

`ranking_scores.csv` および `<job>_summary_confidences.json` の `ranking_score` は次式で計算されます:

```
ranking_score = 0.8 × ipTM
              + 0.2 × pTM
              + 0.5 × fraction_disordered
              - 100 × has_clash
```

- 範囲: `[-100, 1.5]`
- 主目的: **同一ジョブ内のサンプル間比較**（どのサンプルを採用するか）
- `has_clash=True` のサンプルは -100 の減点で最下位になる

> [!IMPORTANT]
> **`ranking_score` は結合親和性 (Kd, IC50) やリガンド活性の予測値ではありません**。
> ジョブ間で `ranking_score` を単純比較して「サンプル A の方が活性が高い」等の結論を出さないでください。
> リガンド活性の推定は AF3 の設計目的外です。

## 5. 複合体（Multimer / リガンド）の解釈

複合体では以下を追加で確認してください:

| フィールド | 意味 |
|-----------|------|
| `chain_pair_iptm` | 鎖ペアごとの ipTM 行列（例: A-B, A-C, B-C）|
| `chain_pair_pae_min` | 鎖ペアごとの PAE 最小値 |
| `chain_ptm` | 各鎖単独の pTM |
| `chain_iptm` | 各鎖の他鎖に対する ipTM 平均 |

PAE (Predicted Aligned Error) ヒートマップの見方:

```python
import json
import numpy as np
import matplotlib.pyplot as plt

with open("/mnt/af3/outputs/tetr_dimer_tetracycline/tetr_dimer_tetracycline_confidences.json") as f:
    conf = json.load(f)

pae = np.array(conf["pae"])
plt.figure(figsize=(6, 5))
plt.imshow(pae, cmap="viridis", vmin=0, vmax=30)
plt.colorbar(label="PAE (Å)")
plt.xlabel("Token index"); plt.ylabel("Token index")
plt.title("PAE heatmap")
plt.savefig("pae.png", dpi=150)
```

- **ブロック状に PAE が低い領域** → その領域内は相対配置が確実
- **鎖境界で急に PAE が高くなる** → 鎖間の相対配置が不確実
- リガンドと結合ポケット残基の PAE が低ければ、そのポケット配置は信頼できる

## 6. 可視化（ChimeraX / Mol* / PyMOL）

### ChimeraX（推奨）

AF3 を扱うなら **ChimeraX 1.8 以降** を使うのが最も簡単です。

```
open /path/to/model.cif
color bfactor palette alphafold
```

### Mol* Web Viewer（ブラウザ）

<https://molstar.org/viewer/> にアクセスし、mmCIF をドラッグ&ドロップ。
「Structure Properties → B-factor coloring」で AlphaFold カラー表示。

### PyMOL

```pymol
load /path/to/model.cif, af3
spectrum b, blue_white_red, af3, minimum=50, maximum=90
```

### py3Dmol (Jupyter)

```python
import py3Dmol

with open("/mnt/af3/outputs/ubiquitin_monomer/ubiquitin_monomer_model.cif") as f:
    cif = f.read()

view = py3Dmol.view(width=600, height=500)
view.addModel(cif, "cif")
view.setStyle({}, {"cartoon": {"colorscheme": {
    "prop": "b", "gradient": "roygb", "min": 50, "max": 90
}}})
view.zoomTo()
view.show()
```

## 7. 妥当性検証（既知構造との比較）

予測構造の**妥当性検証**には既知構造との比較が有効です:

- **Foldseek** — <https://search.foldseek.com/search> に mmCIF をアップロードして数秒で全 PDB + AF-DB を検索
- **TM-align** — <https://zhanggroup.org/TM-align/> でペアワイズ TM-score を計算
- **DALI** — <http://ekhidna2.biocenter.helsinki.fi/dali/>

TM-score > 0.5 なら同一折りたたみ、> 0.9 で実験構造とほぼ同一。

## 8. 品質フィルタリング（バッチ処理時）

```python
import json
import glob
import os

rows = []
# トップランクの summary_confidences (ジョブ名でプレフィクスされる)
for path in glob.glob("/mnt/af3/outputs/*/*_summary_confidences.json"):
    # サンプル別ファイル (_seed-*_sample-*) は除外し、トップランクのみ集計
    if "_seed-" in os.path.basename(path):
        continue
    with open(path) as f:
        s = json.load(f)
    rows.append({
        "job": os.path.basename(os.path.dirname(path)),
        "ptm": s.get("ptm"),
        "iptm": s.get("iptm"),
        "ranking_score": s.get("ranking_score"),
        "has_clash": s.get("has_clash"),
        "fraction_disordered": s.get("fraction_disordered"),
    })

import pandas as pd
df = pd.DataFrame(rows)
print(df)

# 例: 複合体で高品質と判定できるもの
high_quality = df[(df["iptm"] > 0.8) & (df["has_clash"] == False)]
```

## 9. リガンド予測に固有の注意

- **化学的妥当性チェック必須**: chirality (立体配置), valence (原子価), planarity, bond geometry
- **CCD リガンド**: 事前定義された座標を参照するため、既知結合姿勢バイアスがかかる可能性
- **SMILES リガンド**: プロトン化状態を明示（AF3 は既定の水素化状態を仮定）
- **AutoDock Vina, Glide, DiffDock, DiffDock-L 等の別手法と比較**して姿勢の頑健性を確認
- **共有結合リガンド**は `bondedAtomPairs` フィールドを使うが、予測精度は非共有結合より低い

## 10. 次のステップ（研究者向け）

| 目的 | 推奨ツール |
|------|-----------|
| **結合部位予測（別手法）** | PrankWeb, P2Rank |
| **リガンドドッキング検証** | AutoDock Vina, DiffDock-L, Glide |
| **既知構造との類似性検索** | Foldseek, DALI |
| **分子動力学 (MD) 検証** | GROMACS, OpenMM |
| **界面残基同定と変異設計** | PyMOL InterfaceResidues, Rosetta InterfaceAnalyzer |
| **結合親和性推定** | Rosetta, FEP+, PBSA（AF3 の ranking_score では代用不可） |

## 完了チェック

- [ ] `model.cif` を ChimeraX / Mol* / PyMOL で開き、AlphaFold カラーで表示できる
- [ ] `summary_confidences.json` の `ptm`, `iptm`, `ranking_score` の意味を理解した
- [ ] リガンドを含む場合、化学的妥当性を目視でチェックした
- [ ] `TERMS_OF_USE.md` を出力ディレクトリ内に保持している
- [ ] **予測構造は仮説であり実験検証が必須** であることを理解した

**次**: [05-cleanup.md](05-cleanup.md) — 課金停止と DB の永続化オプション
