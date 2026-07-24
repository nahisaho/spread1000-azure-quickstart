# 07. 倫理と限界

## この教材の位置付け

- **教育用途に限定**: 実際の意思決定 (人物評価、コンテンツモデレーション、投資判断) に本教材の出力を使わないでください
- **合成データ**: すべての同梱テキストは AI 生成 + 人手キュレーションの CC0 データで、実在の人物・団体・場所と一切の関係はありません
- **少量データ**: 30〜60 件のデータで得られる分類精度・クラスタ品質は、統計的にも実務的にも不十分です

## 偽情報検出の重大な限界

`synthetic_disinformation.csv` を使った二値分類は、以下の理由で**実運用に耐えない**参考実装です:

1. **合成データにない攻撃的表現の見逃し**: 実データは政治・医療・災害など多様なドメインを含み、学習分布外の入力に対して過信しがち
2. **文脈依存の真偽**: 「昨日雨が降った」という文は文脈次第で真偽が変わる。埋め込み類似度では判定不能
3. **語彙の偏り**: モデルは「陰謀論的表現」を語彙ヒューリスティックで拾うため、風刺・引用・仮説提示を誤検出しやすい
4. **法的責任**: 表現の分類結果を根拠に配信停止・アカウント停止を行うと、名誉毀損 / プロバイダ責任法上のリスクが生じます

実運用には以下が必須です:

- **一次資料検索**: 主張の根拠 URL を提示する検索 (RAG)
- **人間ファクトチェッカー**の最終判断
- **第三者機関** (例: [IFCN 加盟団体](https://www.ifcncodeofprinciples.poynter.org/)) との連携
- 判定結果の**説明責任**と**異議申し立て**手段

## Azure OpenAI の abuse monitoring / データ地理

Azure OpenAI Service では、既定で以下のログ保持・レビューが Microsoft 側で行われます:

- **Prompt / Completion の 30 日保持**: コンテンツフィルタや利用規約違反検出のため、Microsoft が管理するストレージに 30 日間ログが保持されます (お客様のテナントとは分離)。
- **自動 abuse monitoring**: すべての推論トラフィックが自動スキャンされます。
- **限定的な human review**: 高スコアで自動検出された場合、Microsoft の許可された担当者がレビューする可能性があります。

これを無効化するには **modified abuse monitoring** の承認が必要です:

- 申請フォーム: [Modified content management for Azure OpenAI Service](https://aka.ms/oai/modifiedaccess) (2026-07 時点)
- 承認には正当な利用理由 (法定守秘義務、機微研究データ等) の説明が必要
- 個人情報 / 医療情報を扱う場合は、**申請前に自機関の IRB / ELSI 委員会** の助言を受けてください

### Deployment SKU とデータ地理 (GlobalStandard vs Regional/DataZone)

本 quickstart は簡便さのため `GlobalStandard` SKU (gpt-5.4-mini) を既定にしていますが、GlobalStandard は Microsoft が空きキャパのある任意の Azure geography に推論トラフィックをルーティングします。要件により以下を選択してください:

| SKU | 推論処理地域 | 想定用途 |
|---|---|---|
| `GlobalStandard` | 全世界 (可用性優先) | 教材・PoC。個人情報を含まないデータ |
| `DataZoneStandard` | 承認された data zone (例: APAC / EU) 内 | GDPR / APPI 越境制限がある場合 |
| `Standard` (Regional) | 単一 Azure region (例: Japan East) | 完全に日本国内で処理を完結させたい場合 |

Embedding (`text-embedding-3-small`) は Regional Standard で使用しています (`main.bicep` を参照)。

### GDPR / APPI 越境データ移転

- **APPI (個人情報保護法) 第 28 条**: 外国の第三者への提供は原則として本人同意が必要 (Azure は「取扱いを委託する場合」に該当し得るが、要件次第)。詳細は [PPC ガイドライン](https://www.ppc.go.jp/personalinfo/legal/guidelines_offshore/) を参照。
- **EU 居住者データを扱う場合**: GDPR 上の SCC (Standard Contractual Clauses) が Microsoft の [DPA](https://www.microsoft.com/licensing/docs/view/Microsoft-Products-and-Services-Data-Protection-Addendum-DPA) にすでに含まれるが、越境移転の目的正当化 (Art. 45–49) を確認してください。
- 本 quickstart の合成データ (`data/synthetic_*.csv`) は個人情報を含まないため、SKU 選択は原則自由です。



実データを扱う際は **[個人情報保護法](https://laws.e-gov.go.jp/law/415AC0000000057)** の要件に従ってください。

- 氏名・住所・電話番号・メール・SNS ハンドル等は事前にマスクまたは仮名化
- 特別要配慮個人情報 (病歴、犯罪歴、思想信条等) は原則利用しない
- クラウドサービスへの送信は所属機関の**倫理審査 (IRB)** の承認範囲内で行う

参考: [PPC「生成 AI サービスの利用に関する注意喚起等」](https://www.ppc.go.jp/news/press/2023/20230602/)

## 著作権と利用許諾

- 実在の SNS 投稿・ニュース記事・レビュー本文を無許諾でコピーして本教材に取り込まないでください
- 論文引用や研究データ利用は各媒体・データ提供元のライセンス条件を確認してから
- 参考: [文化庁「AI と著作権」](https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html)

## モデル出力の記録

- `data/embeddings/*.manifest.json` にモデル名・バージョン・実行時刻・トークン数が保存されます
- `data/output/*-labels.json` にラベル生成に使ったモデル・reasoning_effort が保存されます
- 論文・発表で数値を引用する際は、必ず manifest から**モデル版**を明記してください

## 参考 (2026-07 時点で確認)

- [経済産業省・総務省『AI 事業者ガイドライン (第1.0版)』](https://www.meti.go.jp/press/2024/04/20240419004/20240419004.html)
- [文化庁『AI と著作権』](https://www.bunka.go.jp/seisaku/chosakuken/aiandcopyright.html)
- [個人情報保護委員会 (PPC) 生成 AI 注意喚起 (2023-06)](https://www.ppc.go.jp/news/press/2023/20230602/)
- [MEXT SPReAD-1000 特設ページ](https://www.mext.go.jp/aifors_spread/)
- [Azure OpenAI Responsible AI 実装ガイド](https://learn.microsoft.com/azure/ai-foundry/responsible-ai/openai/overview)
