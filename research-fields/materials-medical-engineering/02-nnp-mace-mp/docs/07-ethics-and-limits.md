# 07 — 倫理・ライセンス・科学的限界

## ライセンス

### ソフトウェア

| コンポーネント | ライセンス | 引用要求 |
|---|---|---|
| `mace-torch` コード | **MIT** | Zenodo DOI: 10.5281/zenodo.14103332 |
| **MACE-MPA-0** モデル重み | **MIT** | Batatia et al. 2023 (arXiv:2401.00096) |
| MACE-MP-0a/0b/0b2/0b3 モデル重み | **MIT** | 同上 |
| ASE | LGPL v2.1+ | Larsen et al. 2017 (10.1088/1361-648X/aa680e) |
| PyTorch | BSD | — |

### ⚠️ 使ってはいけないモデル (ASL: Academic Software License)

以下のモデルは **非商用限定**。商用利用や、営利組織との共同研究では別途契約が必要:
- `medium-omat-0` (MACE-OMAT)
- `mh-0` / `mh-1` (MACE-MH)
- `matpes-pbe` (MACE-MATPES)

本クイックスタートのスクリプトは **MIT モデル (medium-mpa-0 が既定)** のみを推奨します。

### 学習データのライセンス

MACE-MPA-0 の学習に使われた **MPtrj** データセット (Materials Project trajectories) は **CC BY 4.0** です。**GNoME 構造 (Google DeepMind) は CC BY-NC 4.0** なので、本クイックスタートでは意図的に使用していません。

### 引用義務

論文・発表で MACE-MP を使った場合、以下を必ず引用してください:

```bibtex
@article{batatia2023foundation,
  title={A foundation model for atomistic materials chemistry},
  author={Ilyes Batatia and Philipp Benner and Yuan Chiang and Alin M. Elena and
          Dávid P. Kovács and Janosh Riebesell and others},
  year={2023},
  eprint={2401.00096},
  archivePrefix={arXiv},
  primaryClass={physics.chem-ph},
  doi={10.1063/5.0257345}
}
```

## 科学的限界と注意事項

### 1. DFT-PBE の系統誤差を継承する

MACE-MPA-0 は **PBE / PBE+U 汎関数のデータで学習** されています。したがって MACE の予測は「DFT-PBE を高速に模倣」しているのであり、**実験値と直接比較する場合は PBE 由来の系統誤差**（バンドギャップ過小評価、d 電子局在化の欠如、van der Waals 相互作用の欠落など）を認識してください。

- **バンドギャップ**: NNP 自体はバンドギャップを予測しない。エネルギー・力・応力のみ
- **格子定数**: PBE は実験値より 0.5〜2% 大きく予測しがち
- **バルクモジュラス**: 10〜20% の誤差が典型
- **反応エネルギー**: 系による

### 2. 元素・化学環境のカバレッジ

- MACE-MPA-0 が学習済み: **89 元素**（原子番号 1〜83、希ガス除く）
- **非対応**: 超ウラン元素（Th, U 以上）、ランタノイド系はデータが少ない
- **注意**: 非対応元素を含む系を入力すると、`Element X not in model` の例外が出ます

### 3. 磁性・励起状態は扱えない

- スピン分極や磁気秩序は明示的に扱えない（学習データがスピン平均されているため）
- 電子励起状態、光化学反応も予測不可
- これらは TDDFT や GW-BSE など別手法が必要

### 4. NNP 一般の限界

- **学習分布外 (OOD) の構造** で誤差が発散する可能性がある
  - 例: 学習には無い高圧相、極端に長い/短い結合、遷移状態
- **短距離のクーロン反発**（原子同士がめり込むような構造）で unphysical になりうる
- **長距離相互作用**（分散力、静電）は明示的に含まれない → van der Waals 系や有機分子・液体で誤差大

### 5. MD の統計的信頼性

- 本クイックスタートの 5 ps MD は **動作確認・可視化用の最小構成**
- 熱力学量（自由エネルギー、拡散係数、粘性など）を求めるには **数十 ns 以上、数百原子** が必要
- Langevin thermostat は温度制御には優れるが、動力学的性質（振動スペクトルなど）を歪めるため、正確な計算には Nosé-Hoover や NVE を検討

### 6. 再現性

- `--dtype float32` は数値誤差が ~1 meV/atom オーダーで発生します
- 論文品質の緩和では `--dtype float64` を推奨（速度は半分程度に落ちます）
- Langevin MD は乱数を含むため、シードを固定しても異なるハードウェア間で完全な再現は困難

## 責任ある利用

- **未検証の予測を材料設計の唯一の根拠にしない**。実験または DFT の直接計算で必ず検証してください
- 論文発表時は使用した MACE のバージョン (`pip show mace-torch`)・モデル・dtype・PyTorch バージョンを Methods に明記してください
- **AI モデルの出力を人間の判断なしに製造・臨床応用に転用してはいけません**

## 参考文献

1. Batatia et al., "A foundation model for atomistic materials chemistry", arXiv:2401.00096 (2023). DOI:10.1063/5.0257345
2. Deng et al., "CHGNet: Pretrained universal neural network potential for charge-informed atomistic modeling", *Nature Machine Intelligence* 5, 1031–1041 (2023). DOI:10.1038/s42256-023-00744-w — MPtrj 学習データの原典
3. Jain et al., "The Materials Project: A materials genome approach to accelerating materials innovation", *APL Materials* 1, 011002 (2013). DOI:10.1063/1.4812323
4. Larsen et al., "The Atomic Simulation Environment—a Python library for working with atoms", *J. Phys. Condens. Matter* 29, 273002 (2017). DOI:10.1088/1361-648X/aa680e
