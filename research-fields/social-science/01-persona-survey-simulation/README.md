# 01 — LLM ペルソナ調査シミュレーション

仮想ペルソナ (age_group / gender / region / values 等) と Likert 5 段階の質問群を与え、**Azure OpenAI** の **Structured Outputs** で各ペルソナの回答を生成します。生成された回答分布を χ² 検定 + Cramér's V で分析し、モデルの回答バイアスや人口統計群間の差を可視化します。

> [!IMPORTANT]
> **合成回答は人間データではありません。**
> - 母集団推定・因果推論・世論調査代替には**使わないでください**
> - 実人間の追試なしに科学的主張を行わないでください
> - 詳細は [`docs/06-ethics-and-limits.md`](docs/06-ethics-and-limits.md) を必読

## 何を得られるか

- Azure OpenAI (gpt-4.1-mini, Japan East Regional) を Bicep で構築
- Managed Identity + AAD 認証 (API キーなし、`disableLocalAuth: true`)
- 5 ペルソナ × 10 質問 = 50 回答の自動生成 (Structured Outputs で Likert 整数を強制)
- CSV 出力 (persona_id, question_id, score, label, short_reason, model, system_fingerprint)
- χ² 検定 + Cramér's V による人口統計別の回答差分析

## コスト

| 項目 | 実行中 | 停止中 |
|---|---:|---:|
| Azure OpenAI (gpt-4.1-mini, 50 calls) | **$0.008〜0.02** | $0 |
| Log Analytics (最小構成) | 月額 $1 未満 | 同左 |
| **合計 (1 デモ実行)** | **約 $0.01〜0.10 (¥1.5〜15)** | — |

> [!NOTE]
> Azure OpenAI リソースそれ自体は**課金無し**（トークン使用のみ課金）。ACR や VM のような固定課金リソースは使いません。停止不要ですが、使い終わったら RG ごと削除するのが最も簡単です。

## 前提

- Azure サブスクリプション (Owner または Contributor + User Access Administrator)
- **Azure OpenAI 利用申請が承認済み** (2026 年時点、通常は自動承認)
- **Bash 環境** (WSL2 / Linux / macOS / Cloud Shell)
- az CLI v2.60+
- Python 3.10+

## 実行順序

| # | 手順 | 所要 |
|---:|---|---:|
| 01 | [事前準備](docs/01-prerequisites.md) — az login, リージョン確認, Python 環境 | 10 分 |
| 02 | [Azure OpenAI デプロイ](docs/02-provision-aoai.md) — Bicep で AOAI + gpt-4.1-mini | 5 分 |
| 03 | [ペルソナ・質問の準備](docs/03-prepare-personas.md) — デモ CSV を確認/カスタム | 5 分 |
| 04 | [シミュレーション実行と分析](docs/04-run-and-analyze.md) — Python で回答生成 + χ² 分析 | 5 分 |
| 05 | [クリーンアップ](docs/05-cleanup.md) — RG を削除 | 3 分 |
| 06 | [倫理・限界](docs/06-ethics-and-limits.md) — 必読 | 5 分 |

## モデル選定の根拠

| モデル | 入力 $/1M | 出力 $/1M | Japan East | 判定 |
|---|---:|---:|---|---|
| gpt-4o-mini | 0.15 | 0.60 | **Global のみ**（推論は国外の可能性） | データ主権が問題ならNG |
| **gpt-4.1-mini (推奨)** | **0.40** | **1.60** | **Regional 可** | **本シナリオ既定** |
| gpt-4.1 | 2.00 | 8.00 | Global のみ | 高精度だが本デモ過剰 |
| gpt-4o | 2.50 | 10.00 | Regional 可 | 5× 高いだけ |
| gpt-5 / o-series | 1.10〜 | 4.40〜 | 主に Global | 推論オーバースペック |

出典: [Azure Foundry モデル利用可能性マトリックス](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability?pivots=standard)

> [!NOTE]
> 価格は 2026 年 7 月時点の list price。実際の値は必ず [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) で確認してください。

## ライセンス

- 本ドキュメントと `src/`, `infra/`, `scripts/`: MIT
- Azure OpenAI 出力: Microsoft Product Terms に従う
- 使用しているデモデータ (`data/personas-demo.csv`, `data/questions-demo.csv`): 完全に架空、CC0

## 参考文献

- Bisbee et al. (2024) *Synthetic Replacements for Human Survey Data? The Perils of Large Language Models.* PNAS Nexus. https://doi.org/10.1093/pnasnexus/pgae533
- Salecha et al. (2024) *Large Language Models Show Human-like Social Desirability Biases in Survey Responses.* arXiv:2405.06058
- Argyle et al. (2023) *Out of One, Many: Using Language Models to Simulate Human Samples.* Political Analysis 31(3). https://doi.org/10.1017/pan.2023.2

## トラブルシューティング

問題が起きたら [`troubleshooting.md`](troubleshooting.md) を参照してください。
