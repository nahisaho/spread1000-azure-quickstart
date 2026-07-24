# 電子カルテ日本語 NLP を Azure OpenAI + AI Search で RAG 化（EHR-NLP RAG）

> **研究分野**: 臨床科学 / **想定 SPReAD-1000 課題**: 電子カルテ・退院サマリ・診療記録などの臨床テキストを対象とした情報抽出・要約・検索・Q&A
> **所要時間**: 初回 90 分（プロビジョニング + サンプルデータ投入 + 動作確認 + クリーンアップ）
> **想定コスト**: **本 quickstart の一連の手順（PoC 相当・90 分・合成データ数十件）で ~$0.5–2 USD**（内訳: AI Search Basic ~$0.13/hour × 2h ≈ $0.26、Azure OpenAI トークン ≈ $0.10、Storage/Log Analytics ≈ 数セント）。Japan East 2026-06 Pay-As-You-Go 参考価格。**リソースを消し忘れると 1 日 $3+、1 月 $100+ になり得る**ため §5 のクリーンアップは必ず実施してください。
> **難易度**: ★★☆☆☆（GUI + CLI + Python）

---

## ⚠️ 最重要注意 — 本テンプレートは合成データ専用（実患者データ厳禁）

このクイックスタート（および同梱の Bicep テンプレート）は **合成データ（synthetic data）による動作確認・学習専用** です。以下のように**実患者データを扱うために必要な多層防御が意図的に外されています:**

- Storage / OpenAI / AI Search は **公開エンドポイント**（Private Endpoint / VNet 統合なし）
- Storage は **Microsoft-managed 暗号化のみ**（顧客管理鍵 CMK 非対応）
- Storage は **共有キー（Shared Key）認証も有効**
- Azure OpenAI は **ローカル認証（API キー）も有効**
- 診断ログは 30 日保持のみで長期監査保管なし
- Content Safety / RAI policy はデフォルトのみ

> [!WARNING]
> **本テンプレートで実患者データを扱わないでください。** 実データ運用には Private Endpoint、CMK、共有キー無効化、DLP、監査ログ長期保管、Content Safety カスタムなどを追加した**別テンプレート**が必要です。厚労省「医療情報システムの安全管理に関するガイドライン **第 7.0 版 (2026 年 6 月)**」/ 3 省 2 ガイドライン（システム: 厚労省 7.0、事業者: 経産省・総務省 **v2.0 (2025 年 3 月)**）/ **個人情報保護法（現行法および 2026 年改正に関する動向）** の要件を満たす構成にした上で、以下を必ず確認してください:

1. **所属機関の IRB（倫理審査委員会）承認**を得ている（人を対象とする生命科学・医学系研究倫理指針）
2. **情報セキュリティ委員会**の承認・機関のクラウド利用ポリシー適合を確認済み
3. **法的根拠の選択**を明確にする。医療記録は **要配慮個人情報** であり、以下のいずれかを **明示的に選択・記録**すること:
   - **本人同意 (オプトイン)** — 通常の APPI 上、要配慮個人情報の第三者提供・研究利用に必要
   - **委託** (病院内での処理として研究者が受託) — APPI 27 条 5 項 1 号
   - **学術研究例外** (自機関の学術研究として実施、APPI 18 条 3 項 5-6 号) — 個人の権利利益保護に配慮
   - **次世代医療基盤法** — 「認定匿名加工/仮名加工医療情報作成事業者」への提供スキームで **オプトアウト式**が可能。**通常の APPI オプトアウト第三者提供は要配慮個人情報には使えません**。
4. Azure OpenAI の [**abuse monitoring 変更 / データ格納の権利放棄**](https://learn.microsoft.com/ja-jp/azure/ai-foundry/openai/concepts/abuse-monitoring) について、Microsoft 側の人手レビュー用ログ保管を停止する承認申請済み（自動フィルタリング自体は無効化不可）
5. データが Japan East / Japan West 内に留まる **リージョン指定**
6. **匿名化・仮名加工処理**（氏名・住所・電話・保険者番号・ID 等の削除に加え、日時のシフト、稀な傷病名の粒度調整）が完了している

> [!CAUTION]
> 上記のいずれかを満たさず実データを投入した場合、機関の情報セキュリティ規程・個人情報保護法・「医療情報システムの安全管理に関するガイドライン **7.0 (2026-06)**」等に違反する可能性があります。本 quickstart の同梱サンプル ([inputs/sample-notes/](inputs/sample-notes/)) はすべて GPT-4 で生成された合成データで、実在の患者・症例とは無関係です。

---

## このクイックスタートで実行できること

- 日本語の臨床テキスト（退院サマリ・カルテ抜粋）を Azure Blob Storage にアップロード
- Azure AI Search でベクトル + キーワードのハイブリッドインデックスを構築（`text-embedding-3-large` を使用）
- Azure OpenAI (`gpt-4o` — 導入前に `az cognitiveservices model list -l <region>` で GA + 未 retire バージョンを確認) で「特定のカルテに書かれている症状・投与された薬剤・診断」といった**個別カルテを対象にした Q&A（点検索）** に自然言語で回答（RAG パターン）
- 参照元カルテ・該当箇所の**引用付き**で回答

> [!NOTE]
> **本 quickstart はコホート集計・全件横断カウント（例: 「肺炎の患者は何人か」「レボフロキサシンを使った症例数」）には不向き**です。RAG は上位 K 件の検索結果のみを LLM に渡す設計上、K 件を超える件数の集計は原理的に取りこぼしを生みます。件数・頻度・分布を求める用途では、AI Search の `count`/`facet`/`filter` を使った構造化クエリや、事前に構造化抽出したメタデータフィールドに対する集計を別途組み合わせてください。

## 想定ワークロード（SPReAD-1000 該当例）

- 診療記録の要約と QI（Quality Indicator）自動抽出
- 退院サマリからの副作用・有害事象の抽出
- 症例レポートの類似症例検索
- 治験プロトコルの適合性判定支援

---

## 構成

```
02-ehr-nlp-rag/
├── README.md                          # このファイル
├── docs/
│   ├── 01-prerequisites.md            # 事前準備（IRB / OpenAI 利用申請 / quota）
│   ├── 02-provision.md                # Bicep で OpenAI + AI Search + Storage をデプロイ
│   ├── 03-index-documents.md          # 合成カルテを AI Search にインデックス
│   ├── 04-query-rag.md                # RAG で質問応答
│   └── 05-cleanup.md                  # リソースグループ削除
├── infra/
│   ├── main.bicep                     # 全リソースを一括デプロイ
│   ├── parameters.example.json
│   └── deploy.sh
├── scripts/
│   ├── upload_docs.py                 # Blob にアップロード
│   ├── index_docs.py                  # AI Search インデックス作成
│   └── query_rag.py                   # RAG 質問応答
├── inputs/
│   └── sample-notes/                  # 合成カルテ（GPT-4 生成、実在患者と無関係）
└── troubleshooting.md
```

---

## Azure リソース

| リソース | SKU | 用途 | 概算月額（常時稼働） |
|---|---|---|---:|
| Azure OpenAI | `gpt-4o` (Standard) + `text-embedding-3-large` | 生成・埋め込み | 従量（PoC 数百円〜） |
| Azure AI Search | Basic | ベクトル + BM25 ハイブリッド検索 | ~$75 |
| Azure Storage | Standard LRS (Blob) | カルテ生ファイル置き場 | ~¥300 / 10GB |
| Key Vault | Standard | API キー保管 | 従量（ほぼ 0） |
| Log Analytics | Pay-as-you-go | 監査ログ | 従量（PoC ~¥100） |

> [!IMPORTANT]
> **AI Search Basic は「起動＝課金」** です。停止できないため、使い終わったら **必ずリソースグループごと削除** してください（[05-cleanup.md](docs/05-cleanup.md)）。24 時間放置で ~$2.5 / 日。

---

## 前提

以下すべてが完了していること。詳細は [`../../../docs/00-azure-account-setup.md`](../../../docs/00-azure-account-setup.md) と [`docs/01-prerequisites.md`](docs/01-prerequisites.md) を参照。

- Azure サブスクリプション（Contributor + User Access Administrator 以上）
- `az` CLI 2.60+、`python` 3.10+、`bicep` CLI
- **Azure OpenAI サービスの Limited Access（Abuse Monitoring オプトアウト）を申請する場合は事前承認が必要**（合成データのみの動作確認では標準構成のままで OK）
- **IRB・情報セキュリティ委員会の承認は本 quickstart のスコープ外**（合成データのみの動作確認のため不要。実患者データを扱う別テンプレートで別途取得）

---

## 手順（要約）

1. **[01-prerequisites.md](docs/01-prerequisites.md)** — 事前準備・OpenAI 申請確認 (~15 min)
2. **[02-provision.md](docs/02-provision.md)** — Bicep デプロイ (~10 min)
3. **[03-index-documents.md](docs/03-index-documents.md)** — 合成カルテを AI Search にインデックス (~10 min)
4. **[04-query-rag.md](docs/04-query-rag.md)** — RAG で質問応答 (~10 min)
5. **[05-cleanup.md](docs/05-cleanup.md)** — リソースグループ削除 (~5 min)

---

## 次のステップ

このクイックスタートを完了したら、以下を検討できます:

- **Azure AI Foundry の Prompt Flow** で RAG パイプラインを GUI で編集
- **Semantic Kernel** で複数の Search index を使い分けるエージェント化
- **PHI 検出**: 日本語カルテに対応した専用ソリューションを別途組み合わせる（Azure AI Language の PII 検出は日本語対応だが `phi` domain は英語専用のため、氏名・住所・電話番号など汎用 PII しか抽出できない）。運用では **Microsoft Purview DLP + 医療辞書のカスタム分類子** や国内医療 NLP ベンダーの日本語 PHI 検出エンジンを組み合わせることを推奨。
- **CMK（顧客管理鍵）で暗号化強化** → 実データ運用に必須
- **Private Endpoint 化** → 全リソースを VNet 内に閉じる
- **プロンプトの日本語医療特化ファインチューニング**（Azure OpenAI fine-tuning）

## 参考

- Azure OpenAI ドキュメント: <https://learn.microsoft.com/ja-jp/azure/ai-services/openai/>
- Azure AI Search ベクトル検索: <https://learn.microsoft.com/ja-jp/azure/search/vector-search-overview>
- RAG パターン: <https://learn.microsoft.com/ja-jp/azure/architecture/ai-ml/guide/rag/rag-solution-design-and-evaluation-guide>
- 医療 AI 倫理指針（日本医学会連合）: <https://www.jmsf.or.jp/>
- 個人情報保護委員会（医療分野ガイダンス）: <https://www.ppc.go.jp/>
