# 社会科学（Social Science）

SPReAD-1000 第1回公募で **55 課題**が採択された分野です。LLM を用いたペルソナシミュレーション、文書構造化、テキスト分類・センチメント分析などが中心です。

## クイックスタート一覧

| # | シナリオ | 用途 | Azure サービス | 想定コスト (1 回) |
|---:|---|---|---|---:|
| [01](01-persona-survey-simulation/) | **LLM ペルソナ調査シミュレーション** | 仮想ペルソナ × Likert 質問を Structured Outputs で回答生成、χ² バイアス分析 | Azure OpenAI (gpt-4.1-mini) | $0.01〜0.10 (¥1.5〜15) |
| 02 | **歴史・法務文書の LLM 構造化** — 予定 | PDF → JSON 抽出パイプライン (判例・要項・工場名簿) | Azure OpenAI + Document Intelligence | 予定 |
| 03 | **テキスト分類・トピッククラスタリング** — 予定 | AOAI Embeddings + scikit-learn で SNS/レビュー/偽情報分析 | Azure OpenAI Embeddings | 予定 |

## 学習パス（推奨順）

1. **ペルソナ調査シミュレーション** — Azure OpenAI の初回接続、Structured Outputs、Managed Identity 認証を学ぶ最短ルート
2. **文書構造化** — 非構造化 PDF → 構造化データへの実務パイプライン
3. **テキスト分類・クラスタリング** — Embeddings ベクトルと古典 ML の組み合わせ

## 想定される SPReAD-1000 課題例（実データより）

- 「AI代替アンケート」「ペルソナ社会シミュレーション」「LLM 主観的知覚」→ シナリオ 01
- 「判例整備」「工場名簿の構造化」「独禁法違反行為認定」「入試要項比較」→ シナリオ 02
- 「偽情報検出」「SNS ミーム分析」「観光レビュー解析」「金融テキスト可読性」→ シナリオ 03

## 倫理・法的な留意（分野横断）

- **合成回答は人間データではありません**。母集団推定・因果推論には使わないでください。
- 実在人物・被験者データを扱う場合は、必ず所属機関の **IRB / 倫理審査** を通してください。
- Azure OpenAI のデプロイタイプ (Global / Data Zone / Regional) によって推論の実行ロケーションが異なります。日本国内処理を保証するには **Standard/Regional** デプロイが必要です。

一次資料: [`../../docs/source/spread1000-adopted.json`](../../docs/source/spread1000-adopted.json)（社会科学 55 件）
