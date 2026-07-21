# ESMFold — タンパク質構造予測クイックスタート

> **対象**: MEXT SPReAD-1000 採択者（生命科学・薬学分野）で、単一配列からタンパク質 3D 構造を高速予測したい研究者
> **所要時間**: 約 60 分（デプロイ 15 分 + 環境構築 10 分 + 推論 数十秒〜数分）
> **想定コスト**: T4 で 1 セッション（2 時間）**約 ¥320**、A100 で **約 ¥1,720**

## 何ができるか

Meta AI の **ESMFold**（`facebook/esmfold_v1`, MIT License, 3B パラメータ）を Azure Machine Learning 上で実行し、以下を得ます。

- **アミノ酸配列 → 3D 構造（PDB）** を **数秒〜数十秒** で予測（AlphaFold2 の 10〜60 倍高速）
- 残基ごとの **pLDDT 信頼度スコア**（0〜100）を PDB の B-factor 列と数値配列の両方で取得
- **MSA（多重配列アラインメント）不要** — 新規/エンジニアリング配列でも即座に予測可能
- FASTA ファイルからの **バッチ推論**（数百〜数千配列を夜間処理）

```mermaid
flowchart LR
  FASTA[入力配列 FASTA] --> HF[HuggingFace<br/>facebook/esmfold_v1<br/>8.44 GB]
  HF --> AML[Azure ML<br/>Compute Instance]
  AML --> CI[GPU コンピュート<br/>T4 16GB or A100 80GB]
  CI -->|inference 数秒〜数十秒| OUT[構造 PDB<br/>+ pLDDT 配列 CSV]
  OUT --> VIS[py3Dmol / PyMOL で可視化]
```

## ⚠️ AI 予測構造の解釈に関する注意

ESMFold は **予測モデル** であり、生成された構造は **実験的に検証されるまでは仮説** です。以下を必ず理解してください。

- **pLDDT < 50 の領域は無秩序（IDR）または低信頼**。折りたたみ構造として解釈しない
- **pLDDT 70–89 は「概ね正しい」、90+ は「側鎖まで信頼可」** の目安（AlphaFold2 と同じスケール）
- **オリゴマー・複合体は予測しません**（単鎖のみ）。多量体は AlphaFold-Multimer や AlphaFold3 を使う
- **点変異の影響予測は苦手** — ESMFold は野生型に近い予測を返しがち
- **公表・特許出願時は必ず実験検証**（X 線結晶構造、CryoEM、NMR、機能アッセイのいずれか）を組み合わせる

出典: Lin et al. (2023) *Science* 379:6637, 1123–1130; ESM チーム FAQ。

## いつ ESMFold を選ぶか

| 用途 | 推奨ツール |
|---|---|
| 数千配列のハイスループット構造トリアージ | **ESMFold** ✅ |
| 新規配列（既知ホモログなし）の構造推定 | **ESMFold** ✅ |
| 単鎖の 300〜700 aa の高速予測 | **ESMFold** ✅ |
| 高精度（TM-score > 0.9）が必要 | AlphaFold2 / ColabFold |
| タンパク質複合体・多量体 | AlphaFold-Multimer / AlphaFold3 |
| タンパク質–リガンド複合体 | AlphaFold3 |
| >1024 aa の大きな単鎖 | AlphaFold2（ドメイン分割）または ESMFold + ドメイン分割 |

## セキュリティ・データガバナンス

- 入力配列（FASTA）はコンピュート上の一時ディスクに保存されます。**特許・企業機密配列** を扱う場合は、`~/cloudfiles/` へ保存せず、実行後に必ず削除してください
- Azure ML Workspace の依存 Storage/KV は既定で **暗号化 (Microsoft-managed key)**。BYOK（顧客管理鍵）が必要な場合は Bicep で `encryption` ブロックを追加してください
- **HuggingFace からのモデルダウンロードは Zenodo/HF のパブリック CDN を経由します**。イントラネット限定運用が必要なら、事前に重みを Azure Blob にキャッシュしてください（`docs/troubleshooting.md` 参照）

## Azure リソース構成とコスト

| リソース | SKU / 数量 | japaneast 料金（PAYG） |
|---|---|---|
| **Standard_NC8as_T4_v3**（推奨・低コスト） | T4 16GB × 1 | 約 US$1.02/h（≒ ¥160/h） |
| Standard_NC24ads_A100_v4（高速・長鎖用） | A100 80GB × 1 | 約 US$5.33/h（≒ ¥860/h） |
| Standard_NC4as_T4_v3（最安・実験用） | T4 16GB × 1 | 約 US$0.71/h（≒ ¥110/h） |
| Standard_NC40ads_H100_v5（超高速） | H100 80GB × 1 | 約 US$10.12/h（≒ ¥1,620/h） |
| Azure ML Workspace（本体） | 1 | 無料（依存リソースのみ課金） |
| Storage Account (StandardV2, LRS) | 1 | 数十〜数百円/月 |
| Key Vault (Standard) | 1 | 数十円/月 |
| Application Insights | 1 | データ取込量に応じて |
| Container Registry (Basic) | 1 | 約 ¥800/月 |

> **T4 で 300 aa なら数十秒／推論**。1 セッション 2 時間の実験で **¥300 前後**が現実的です。

**総所要コスト目安**（推論 1 回、Compute 稼働 2 時間）：
- T4 で **約 ¥320**
- A100 で **約 ¥1,720**
- H100 で **約 ¥3,240**

依存リソースは削除しない限り月数百円〜千円の課金が発生します。プロジェクト完了時は [05-cleanup.md](docs/05-cleanup.md) に従い **リソースグループごと削除** してください。

## 手順

| ステップ | ドキュメント | 時間 |
|---|---|---|
| 0. 前提確認 | [docs/01-prerequisites.md](docs/01-prerequisites.md) | 5 分 |
| 1. Workspace + Compute 作成 | [docs/02-provision-aml.md](docs/02-provision-aml.md) | 10 分 |
| 2. ESMFold 環境構築と推論 | [docs/03-run-esmfold.md](docs/03-run-esmfold.md) | 15〜30 分 |
| 3. 結果の解釈（PDB, pLDDT） | [docs/04-interpret-results.md](docs/04-interpret-results.md) | 15 分 |
| 4. クリーンアップ | [docs/05-cleanup.md](docs/05-cleanup.md) | 5 分 |
| — 困ったとき | [docs/troubleshooting.md](docs/troubleshooting.md) | — |

## 何がついてくるか

```
esmfold-structure-prediction/
├── README.md                        ← 本ファイル
├── docs/
│   ├── 01-prerequisites.md          ← Azure サブスクリプション、GPU クォータ
│   ├── 02-provision-aml.md          ← Bicep または deploy.sh
│   ├── 03-run-esmfold.md            ← 環境構築 + 推論実行
│   ├── 04-interpret-results.md      ← pLDDT の見方、可視化
│   ├── 05-cleanup.md                ← 課金停止手順
│   └── troubleshooting.md           ← よくあるエラー
├── infra/
│   ├── main.bicep                   ← Workspace + Compute Instance 定義
│   ├── deploy.sh                    ← ワンクリック デプロイ
│   └── parameters.example.json      ← Bicep パラメータ例
└── scripts/
    ├── setup-esmfold.sh             ← conda 環境と HF cache セットアップ
    ├── run-inference.py             ← 単一/バッチ推論の CLI
    └── examples/
        └── ubiquitin.fasta          ← 動作確認用の 76 aa テスト配列
```

## 参考文献

- Lin, Z. *et al.* (2023). Evolutionary-scale prediction of atomic-level protein structure. *Science* 379:6637, 1123–1130. [DOI:10.1126/science.ade2574](https://www.science.org/doi/10.1126/science.ade2574)
- ESMFold HuggingFace Model Card: https://huggingface.co/facebook/esmfold_v1
- ESM リポジトリ（archived）: https://github.com/facebookresearch/esm
- HuggingFace Colab リファレンスノートブック: https://colab.research.google.com/github/huggingface/notebooks/blob/main/examples/protein_folding.ipynb

## ライセンス

- **本クイックスタート（ドキュメント・スクリプト・IaC）**: MIT License（本リポジトリのルート `LICENSE` に従う）
- **`facebook/esmfold_v1` 重み**: MIT License（商用・改変・再配布可）

---

**次**: [docs/01-prerequisites.md](docs/01-prerequisites.md) — 前提条件と権限
