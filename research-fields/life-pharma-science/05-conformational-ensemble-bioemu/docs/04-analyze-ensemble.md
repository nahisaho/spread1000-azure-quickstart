# 04. 結果解析 (RMSD, Rg, クラスタリング)

## 0. 前提

- [03. Chignolin 100 サンプル生成](03-run-bioemu.md) 完了
- `downloaded/` 配下に `samples.xtc`, `topology.pdb`, `sequence.fasta` がある
- Python 3.11+ + `mdtraj`, `numpy`, `scikit-learn`, `matplotlib` がインストール済み

## 1. リファレンス構造の取得

Chignolin の実験構造 (NMR, PDB `1UAO`) をダウンロード:

```bash
curl -sL https://files.rcsb.org/download/1UAO.pdb -o reference-1uao.pdb
head -5 reference-1uao.pdb
```

## 2. 解析スクリプト実行

```bash
python scripts/analyze.py downloaded --reference-pdb reference-1uao.pdb --outdir analysis
```

出力:

```
analysis/
├── analysis.csv         # frame ごとの rmsd_nm, rg_nm, cluster ラベル
├── rmsd_histogram.png   # Cα RMSD to 1UAO の分布
├── rg_histogram.png     # Rg の分布
└── summary.txt          # 中央値、範囲、cluster 数
```

典型的な `summary.txt`:

```
Frames analyzed:       100
Median Rg:             6.20 Å
Rg 5-95 percentile:    5.80〜7.10 Å
DBSCAN eps (Cα RMSD):  1.50 Å
DBSCAN clusters:       2 (noise frames: 8)
Median RMSD to ref:    1.85 Å
Min RMSD:              0.62 Å
```

## 3. 何を読み取るか

### RMSD ヒストグラム

- **鋭いピーク (< 2 Å)** → BioEmu が native-like 状態を高頻度で生成している (chignolin の期待挙動)
- **バイモーダル (2 つ以上のピーク)** → folded / partially-folded の別々の basin
- **ブロード (5 Å 超まで裾)** → unfolded 状態を含む多様なアンサンブル

### Rg ヒストグラム

- **狭いピーク** → コンパクトな折り畳み構造で安定
- **広い分布 / ダブルピーク** → 折り畳み ↔ 変性の平衡

### DBSCAN クラスタ

- eps = 1.5 Å はβ-hairpin 系向けの推奨値。長いタンパクなら 2〜3 Å に緩める
- **クラスタ数 = 1〜3** が chignolin での典型
- **noise frames** はどのクラスタにも属さない外れ frame (フィルタ後にも残った異常構造の可能性)

> [!IMPORTANT]
> **クラスタ数は eps 値に強く依存します**。単一の数字を「状態数」と解釈しないでください。cluster 数が急変する eps を探して感度分析するのが実務的です。

## 4. PyMOL / ChimeraX で可視化 (任意)

代表 frame を PDB に書き出し:

```python
import mdtraj as md
import numpy as np

traj = md.load_xtc("downloaded/named-outputs/ensemble/samples.xtc",
                   top="downloaded/named-outputs/ensemble/topology.pdb")
labels = np.loadtxt("analysis/analysis.csv", delimiter=",", skiprows=1, usecols=(2,), dtype=int)

for cid in sorted(set(labels) - {-1}):
    idx = int(np.where(labels == cid)[0][0])   # cluster 内 first frame
    traj[idx].save_pdb(f"cluster_{cid:02d}.pdb")
    print(f"cluster {cid}: frame {idx} → cluster_{cid:02d}.pdb")
```

PyMOL:

```
pymol reference-1uao.pdb cluster_00.pdb cluster_01.pdb
```

## 5. 「良い結果」の判断基準

Chignolin における最低限のサニティチェック:

| 指標 | 期待値 | 説明 |
|---|---|---|
| Min RMSD to 1UAO | < 2.0 Å | 少なくとも 1 frame が native に近い |
| Median RMSD | < 4.0 Å | 全体として native basin 周辺 |
| Median Rg | 5〜8 Å | β-hairpin の妥当な値 |
| クラスタ数 | 1〜3 | 大きすぎる場合は eps を上げる |

これらから逸脱する場合:

- **サンプル数不足**: `num_samples` を 1000 に増やす
- **seed の偏り**: 別 seed で複数 run し merge
- **配列不一致**: `sequence.fasta` と `topology.pdb` の残基数を照合

## 6. Chignolin 以外への応用

### Trp-cage (20 残基, `NLYIQWLKDGGPSSGRPPPS`)

- リファレンス: PDB `1L2Y` (NMR)
- 期待クラスタ数: 2〜4 (folded + partially-folded)
- Job wall time: A100 で ~5 分 (コールドスタート除く)

### 100〜200 残基ターゲット

- Rg のスケール変動が大きい → `--rmsd-cutoff-nm 0.3` (3 Å) に緩める
- サンプル 1000 個推奨。**公式ベンチマーク** (A100 80GB, `batch_size_100=20`) は
  100 残基で 4 分、300 残基で 40 分、600 残基で 150 分。
  200 残基は公式値なしですが、二次補間で warm sampler-only 約 16 分の目安 (コールドスタート除く)
- キャッシュは **明示的にマウントを設定した場合のみ**再利用されます (compute は `min_instances: 0`
  でスケールインするため、デフォルトでは AlphaFold params / embeddings は Job ごとに再取得)。
  再利用したい場合は [Troubleshooting §AlphaFold params のオフライン化](troubleshooting.md#alphafold-params-のオフライン化) を参照

## 7. BioEmu アンサンブルを MD の初期構造として使う (発展)

BioEmu は物理的に「厳密」ではないため、以下の workflow が推奨されます:

1. BioEmu で 100〜1000 samples を生成
2. DBSCAN でクラスタリング → 各クラスタの代表 frame を取得
3. 各代表 frame を **OpenMM / GROMACS の初期構造**として MD (100 ns〜1 μs)
4. MD 軌跡から thermodynamic quantity (ΔG, kinetics) を計算

これにより、MD 単体では捕らえにくい **rare basin** の探索を BioEmu が担当し、物理的検証を MD が担当する、という役割分担が成立します。

## チェックリスト

- [ ] `analysis.csv` が出力された
- [ ] `rmsd_histogram.png`, `rg_histogram.png` が可視化できる
- [ ] Median RMSD to 1UAO が 5 Å 以下 (chignolin の場合)
- [ ] クラスタ数と noise 数を確認した

## 次のステップ

→ [05. クリーンアップ](05-cleanup.md)
