# BioEmu — タンパク質コンフォメーションアンサンブル生成 (Azure ML)

**Microsoft BioEmu** を Azure Machine Learning + A100 GPU で動かし、**単一配列からタンパク質の平衡アンサンブル**を生成するクイックスタート。SPReAD-1000 生命科学・薬学領域向け。

## 何ができるか

- アミノ酸配列 1 本 → **100〜1,000 個の独立サンプル構造** (PDB topology + XTC trajectory)
- MD (分子動力学) より **4〜5 桁高速** (fast folder ベンチマーク) で近似平衡分布を生成
- Cryptic pocket 検出、ドメイン運動の予兆、変性状態の探索など
- **AlphaFold / ESMFold との差**: 単一構造ではなく **分布** を返す

> [!IMPORTANT]
> BioEmu は物理エネルギーではなく **学習された経験的な分布** です。300 K 前後・単鎖・標準アミノ酸のみ対応。リガンド / 膜 / 核酸 / 多量体は扱えません。定量的結論は必ず実験または MD で検証してください。

> [!WARNING]
> **データガバナンス**: FASTA を入力すると、BioEmu は MSA 取得のため配列を **公開 ColabFold MMseqs2 API (`api.colabfold.com`)** に送信します。未公開配列・機密配列を扱う場合は、事前にローカルで A3M を生成して入力するか、自前 MMseqs2 サーバの URL を `--msa_host_url` で指定してください。詳細は [Troubleshooting §MSA サービス](docs/troubleshooting.md#msa-サービス-colabfold-がタイムアウトする) 参照。

## ワークロード概要

| 項目 | 内容 |
|---|---|
| モデル | BioEmu v1.1 (Science 2025, DOI 10.1126/science.adv9817) |
| 配布元 | HuggingFace `microsoft/bioemu` (MIT, public/ungated) |
| チェックポイント | ~120 MiB (31M パラメータ) |
| 依存 | Python 3.11+, PyTorch 2.6+, JAX (CUDA 12), TensorFlow-CPU, PyTorch Geometric |
| GPU | A100 80 GB 推奨 (`Standard_NC24ads_A100_v4`) |
| 追加ダウンロード | AlphaFold2 params ~3.5 GB (初回のみ、キャッシュ可能) |
| Azure リージョン | Japan East |

## 想定コスト (Japan East, 2026-07 Retail Prices)

`Standard_NC24ads_A100_v4` (A100 80GB × 1):

| プラン | USD/時 | 円/時 (¥150/USD) |
|---|---:|---:|
| PAYG | $5.326 | ¥799 |
| Spot | $0.984 | ¥148 |

**チュートリアル 1 回 (chignolin 10 残基, 100 サンプル)**: プロビジョニング + 初回ダウンロード含めて 15〜30 分 → **PAYG ¥200〜400 / Spot ¥40〜80**

## 学習パスと所要時間

| # | ステップ | 所要 |
|---:|---|---:|
| [01](docs/01-prerequisites.md) | 前提条件・Azure アカウント準備 | 15 分 |
| [02](docs/02-provision-aml.md) | AML workspace + A100 compute プロビジョニング | 15 分 |
| [03](docs/03-run-bioemu.md) | Chignolin 100 サンプル生成 (Job 実行) | 20 分 |
| [04](docs/04-analyze-ensemble.md) | 結果解析 (RMSD, Rg, クラスタリング) | 15 分 |
| [05](docs/05-cleanup.md) | クリーンアップ | 5 分 |
| [Troubleshooting](docs/troubleshooting.md) | よくある問題と対処 | — |

## ディレクトリ構成

```
05-conformational-ensemble-bioemu/
├── README.md                     # このファイル
├── docs/                         # ステップバイステップ手順
├── infra/
│   ├── main.bicep                # AML workspace (subscription-scope)
│   ├── parameters.example.json
│   └── deploy.sh                 # ワンショットデプロイ
├── aml/
│   ├── Dockerfile                # bioemu[cuda]==1.4.1
│   ├── environment.yml           # AML custom environment
│   ├── compute-a100.yml          # NC24ads_A100_v4 (min=0, Spot 可)
│   └── bioemu-sample.yml         # Command Job 定義
├── scripts/
│   ├── analyze.py                # RMSD/Rg/DBSCAN 解析
│   └── verify-output.py          # XTC 整合性チェック
└── inputs/
    └── chignolin.fasta           # ベンチマーク配列
```

## 前提知識

- Bash と Python の基礎 (コピペで動く手順を提供)
- タンパク質構造の一般的理解 (backbone / RMSD / Rg)
- Azure サブスクリプションが 1 つある (**Owner または Contributor+UAA 権限**)

## 参考文献

- Lewis et al., *Scalable emulation of protein equilibrium ensembles with generative deep learning*, **Science 389:6761 (2025)**, DOI [10.1126/science.adv9817](https://doi.org/10.1126/science.adv9817)
- GitHub: https://github.com/microsoft/bioemu
- Model: https://huggingface.co/microsoft/bioemu
- License: MIT

## 次のステップ

→ [01. 前提条件](docs/01-prerequisites.md)
