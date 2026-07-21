# 06 — 倫理・限界 (必読)

> [!CAUTION]
> LLM ペルソナ回答は **人間の回答ではありません**。世論調査、疫学調査、投票行動予測、消費者調査などの**代替として使うことは科学的にも倫理的にも不適切**です。

このシナリオは、あくまで「モデルがどう回答するか」を測定する研究ツールです。以下を必ず理解してから使ってください。

## 1. 合成回答 ≠ 人間データ

- 生成された回答は **モデルの学習分布から推定された「もっともらしい」回答**です
- 母集団推定、有病率、代表性、統計的推論に**使えません**
- 因果推論の代替になりません
- Bisbee et al. (2024) *Synthetic Replacements for Human Survey Data? The Perils of Large Language Models.* PNAS Nexus. https://doi.org/10.1093/pnasnexus/pgae533

## 2. ペルソナプロンプトはステレオタイプを再現する

- 「30 代女性 会社員」と指示しても、モデルの内部にある**平均的な 30 代女性会社員像**が返るだけ
- 実在の個人の多様性を代表しません
- 少数派・周縁化されたグループはさらに歪んで表現される可能性
- Cheng et al. (2023) *Marked Personas.* ACL 2023. https://aclanthology.org/2023.acl-long.84/
- Wang et al. (2024) *Large Language Models Cannot Replace Human Participants Because They Cannot Portray Identity Groups.* arXiv:2402.01908

## 3. 社会的望ましさバイアス

- LLM は **社会的に望ましい回答**を選ぶ傾向が強いことが実証されています
- 逆転項目 (reverse-worded) を混ぜても完全に相殺されません
- Salecha et al. (2024) *Large Language Models Show Human-like Social Desirability Biases in Survey Responses.* arXiv:2405.06058. https://arxiv.org/abs/2405.06058

## 4. 再現性の限界

- `seed` パラメータは**再現性を近似**するだけで保証しません
- `system_fingerprint` が変わると（モデルのマイナー更新等）、同じ seed でも回答が変わります
- **必ず記録**: model 名, version, deployment (Regional/Global/Data Zone), region, prompt, schema, temperature, seed, system_fingerprint, 実行日時
- 参考: [Reproducible output](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/reproducible-output)

## 5. データ主権 (Data Residency)

- Azure OpenAI のデプロイタイプで推論ロケーションが変わります：
  - **Standard/Regional** (本シナリオ既定): 選択リージョン内で処理
  - **Global Standard**: グローバルの空きキャパで処理 (国外可能性あり)
  - **Data Zone Standard**: 地理ゾーン内 (APAC / EU / US)
- 個人情報を扱う場合は **Regional** 必須。デモの架空ペルソナのみで検証してから拡張してください
- 参考: [Deployment Types](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types)

## 6. IRB / 倫理審査

- 実在被験者の回答パターン模倣、被験者データからのペルソナ生成、集めた回答を人間データとして扱う場合は、**必ず所属機関の IRB (倫理審査委員会)** を通してください
- 個人情報保護法 (2022 改正) の要配慮個人情報 (思想・信条、健康、性的指向等) を扱う場合は特に注意
- 本シナリオの `data/personas-demo.csv` は完全に架空 (CC0) なので IRB 不要

## 7. 公表時の記載事項 (推奨)

論文・レポートで LLM シミュレーションの結果を報告する場合、次を必ず記載してください：

- モデル ID とバージョン (例: `gpt-4.1-mini-2025-04-14`)
- Azure OpenAI デプロイタイプ (Regional / Global / Data Zone) とリージョン
- system prompt (全文)
- response schema (全文または DOI)
- temperature, seed, system_fingerprint
- サンプルサイズ、実行日時
- リフューザル (refusal) 件数と内容
- 複数 seed / 複数モデルでの感度分析結果

## 8. Do / Don't まとめ

| ✅ Do | ❌ Don't |
|---|---|
| モデルのバイアスを測定する研究 | 世論調査の代替として結果を発表 |
| 質問文の pre-test / パイロット設計 | 母集団推定 / 有病率推定 |
| 教育目的の LLM 挙動デモ | 少数派グループの意見を「代表」させる |
| 感度分析 (複数 seed / モデル) | 単一 run を「実験結果」として扱う |
| 架空ペルソナのみで実験 | 実在被験者データからペルソナ抽出（IRB なし） |

## 9. 追加参考文献

- Argyle et al. (2023) *Out of One, Many: Using Language Models to Simulate Human Samples.* Political Analysis 31(3). https://doi.org/10.1017/pan.2023.2
- Santurkar et al. (2023) *Whose Opinions Do Language Models Reflect?* ICML 2023. https://arxiv.org/abs/2303.17548
- Cheng et al. (2023) *Marked Personas: Using Natural Language Prompts to Measure Stereotypes in Language Models.* ACL 2023. https://aclanthology.org/2023.acl-long.84/

---

これらの限界を理解した上で、本シナリオを**モデル研究のためのツール**として活用してください。
