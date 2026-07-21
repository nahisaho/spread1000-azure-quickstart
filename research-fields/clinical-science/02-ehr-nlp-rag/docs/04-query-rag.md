# 04. RAG で質問応答

## 目的

`scripts/query_rag.py` を使って、インデックス化された合成カルテに対して自然言語で質問応答します。

## 前提

- [03-index-documents.md](03-index-documents.md) 完了、インデックス `ehr-notes` に 3 件以上のチャンクが投入済み

## 1. 基本の使い方

```bash
cd research-fields/clinical-science/02-ehr-nlp-rag
set -a && source .env && set +a
source .venv/bin/activate

python scripts/query_rag.py "肺炎球菌肺炎の患者に投与された抗菌薬は？"
```

期待される出力例:

```
============================================================
Question: 肺炎球菌肺炎の患者に投与された抗菌薬は？
============================================================
- レボフロキサシン 500 mg/日（点滴 → 経口）が投与されました [SYNTH-001]
- ペニシリンアレルギー既往のためペニシリン系ではなくキノロン系が選択されました [SYNTH-001]

⚠️ 参照カルテはすべて GPT-4 で生成された合成データです。実患者データではありません。
============================================================
(retrieved 3 chunk(s) from index 'ehr-notes')
```

## 2. サンプル質問集（推奨: 個別カルテ・点検索のみ）

> [!NOTE]
> RAG は Top-K（既定 5）件のチャンクのみを LLM に渡す設計上、**「〜の症例は何人」「〜が最も多い症例」「〜が閾値以上」といった全件横断・集計・最大値クエリは原理的に取りこぼしを生みます**。以下のサンプルは、単一カルテ内の内容確認・引用付き参照に絞っています。集計・件数・分布が必要な場合は AI Search の `$count` / `facet` / `filter` を使った構造化クエリを別途組み合わせてください。

```bash
# 単一カルテ内の情報抽出（点検索）
python scripts/query_rag.py "synth-001-pneumonia のカルテで使用された抗菌薬と投与期間を教えて"
python scripts/query_rag.py "synth-002-stemi の入院時の心電図所見と再灌流療法の内容を教えて"
python scripts/query_rag.py "synth-003-uc の内視鏡所見と治療方針を教えて"

# 症状・診断・処方の該当箇所検索（引用付き）
python scripts/query_rag.py "急性冠症候群と診断された症例の初期治療内容を、該当カルテを引用しつつ説明して"
python scripts/query_rag.py "潰瘍性大腸炎に対して使用された治療薬について記載しているカルテを教えて"
python scripts/query_rag.py "市中肺炎の起炎菌と抗菌薬選択の根拠が書かれたカルテを引用付きで示して"

# 用語・所見の該当箇所抜粋（カルテ記載に基づくもののみ）
python scripts/query_rag.py "STEMI カルテに記載されている再灌流療法のタイプと、Door-to-Balloon 時間があれば引用付きで示して"
```

## 3. パイプラインの内部

`query_rag.py` の処理:

1. **質問の埋め込み化**: Azure OpenAI `text-embedding-3-large` で 3072 次元ベクトルに変換
2. **ハイブリッド検索**: AI Search に対して
    - キーワード検索（BM25 + `ja.microsoft` analyzer）
    - ベクトル検索（HNSW cosine, top-5）
    - Semantic ranker で再ランク（`default-semantic` 設定）
3. **プロンプト構築**: システムプロンプトで「参照カルテ以外の情報を使わない」「引用 [SYNTH-XXX] 必須」「合成データ注記」を強制
4. **生成**: `gpt-4o` (temperature=0) で回答生成

## 4. カスタマイズポイント

`scripts/query_rag.py` の以下を編集して挙動を変えられます:

- `TOP_K = 5` — 取得するチャンク数（大きいほどコンテキスト増、精度↑、トークン↑）
- `SYSTEM_PROMPT` — 回答スタイル、引用形式、追加ルール
- `temperature=0.0` — 決定的な回答（研究用途では推奨、要約系タスクは 0.3 も可）
- `max_completion_tokens=800` — 回答の最大長

## 5. 品質評価の例（研究向け）

RAG システムの評価には以下が使えます:

- **Recall@k / MRR**: 正解が top-k に含まれる割合
- **Groundedness**: 回答が参照カルテに基づいているか（Azure AI Studio の Evaluation SDK）
- **Faithfulness**: ハルシネーション率（GPT-4 で judge）
- **Answer relevance**: 質問との適合度

Azure AI Studio の [Prompt flow evaluation](https://learn.microsoft.com/ja-jp/azure/ai-studio/how-to/evaluate-generative-ai-app) や [Azure AI Evaluation SDK](https://learn.microsoft.com/ja-jp/azure/ai-foundry/how-to/develop/evaluate-sdk) を組み合わせると自動化できます。

## 6. 本番運用に向けた拡張

- **AI Search の Indexer + Skillset** を使うと、Blob 追加を自動検知して埋め込み更新できる（Push モデルから Pull モデルへ）
- **Semantic Kernel** / **LangChain** / **LlamaIndex** でエージェント化
- **PHI マスキング**: 日本語カルテには専用の PHI 検出エンジンを組み合わせる（Azure AI Language の PII 検出は日本語対応だが、`phi` domain は英語専用のため氏名・住所・電話番号など汎用 PII しか抽出できない）。**Azure Content Safety は毒性・ジェイルブレイクフィルタが本来目的で PHI 検出は行いません**。運用では Microsoft Purview DLP のカスタム分類子や、国内医療 NLP ベンダーの日本語 PHI 検出を組み合わせてください。
- **Prompt Flow** で pipeline を GUI で編集・A/B テスト
- **Front-end**: Azure Static Web Apps + React で研究者向け Web UI

## トラブルシューティング

| 症状 | 原因・対応 |
|---|---|
| `Semantic configuration 'default-semantic' not found` | インデックス作成時に semantic が失敗 → Basic SKU で semantic ranker (free tier) は利用可、リージョン依存で提供されていない場合あり。エラーなら `query_type` を削除して純ハイブリッドに切り替え |
| 回答が「参照カルテからは判断できません」ばかり | 該当情報がカルテにない、または `TOP_K` が小さすぎる → `TOP_K=10` に増やす |
| 回答に引用 [SYNTH-XXX] が付かない | `SYSTEM_PROMPT` が守られていない → temperature を下げる、または該当カルテがヒットしていない場合は Top-K を増やす |
| 質問すると数十秒かかる | GPU バックエンドの待ち行列、または TPM 消費 → 別リージョンの OpenAI にフォールバック |
| RateLimit `429` | TPM/RPM 超過 → [`../../../../docs/02-gpu-quota.md`](../../../../docs/02-gpu-quota.md) 相当の要領で Azure Portal から OpenAI 側 quota 増加申請 |

→ **[05-cleanup.md](05-cleanup.md) に進む**
