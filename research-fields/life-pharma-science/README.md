# 生命科学・薬学（Life & Pharmaceutical Sciences）

SPReAD-1000 第1回公募で **98 課題**が採択された最大の分野です。タンパク質構造予測、分子生成、オミクス解析など、AI for Science の中核となるワークロードをカバーします。

## クイックスタート一覧

| # | シナリオ | 用途 | GPU / 計算資源 | 想定コスト (1 回) |
|---:|---|---|---|---:|
| [01](01-molecular-generation-tamgen/) | **TamGen** — target-aware 分子生成 | 標的タンパク構造から候補化合物 SMILES を生成 | NC4as_T4_v3 (Spot) | ¥100〜300 |
| [02](02-protein-structure-esmfold/) | **ESMFold** — 単一配列 protein folding | MSA 不要の高速タンパク質構造予測 | NC24ads_A100_v4 (Spot) | ¥200〜500 |
| [03](03-protein-structure-alphafold3/) | **AlphaFold 3** — 多量体・複合体構造予測 | タンパク質–リガンド / 核酸複合体 | NC24ads_A100_v4 (PAYG) | ¥1,000〜3,000 |
| [04](04-transcriptomics-rnaseq/) | **RNA-Seq (nf-core/rnaseq)** | Bulk RNA-Seq 定量パイプライン | Azure Batch (Spot) | ¥500〜2,000 |

## 学習パス（推奨順）

1. **AlphaFold 3 か ESMFold** — 「タンパク質構造」から入るのが Azure ML と AI モデルの両方に慣れやすい
2. **TamGen** — 分子生成に興味があれば
3. **RNA-Seq** — オミクスなら Nextflow + Azure Batch のワークフロー型

各クイックスタートは独立して動作します。興味のあるものから始めて構いません。

## 想定される SPReAD-1000 課題例（実データより）

- 「AlphaFold を用いた〜」「ESM を用いた〜」→ シナリオ 02 / 03
- 「創薬 AI」「分子設計」「タンパク–リガンド相互作用」→ シナリオ 01
- 「トランスクリプトーム解析」「RNA-Seq」「single-cell」→ シナリオ 04（single-cell は今後追加予定）

## 追加予定

- **BioEmu** — タンパク質コンフォメーションアンサンブル
- **Single-cell (Scanpy on AML)**
- **分子動力学 (OpenMM / GROMACS on GPU)**
