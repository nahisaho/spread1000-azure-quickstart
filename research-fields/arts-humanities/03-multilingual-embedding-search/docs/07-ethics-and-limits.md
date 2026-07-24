# 07 — 倫理と限界

## モデルライセンス

| モデル | ライセンス | 主な義務 |
|---|---|---|
| Azure OpenAI text-embedding-3-large | [Azure 製品条項](https://www.microsoft.com/licensing/terms/) + DPA | Microsoft Responsible AI 標準の遵守、Abuse Monitoring (30 日間ログ保持、承認済み顧客はオプトアウト可) |
| intfloat/multilingual-e5-large | [MIT License](https://huggingface.co/intfloat/multilingual-e5-large) | 再配布時 MIT 表示を保持。クエリには `query: ` プレフィックス、文書には `passage: ` プレフィックスを付与 |

> **E5 使用時の注意**: `EMBED_PREFIX_QUERY="query: "` / `EMBED_PREFIX_DOC="passage: "` を設定し、
> 埋め込み時に入力テキストへ自動付加してください。

## データガバナンスとプライバシー

### 最小必要原則

- インデックスに登録するフィールドは検索・表示に必要なもののみ。
- 機密情報 (個人名、住所、医療情報等) はインデックス登録前に分類・削除またはマスク。
- Azure AI Search の `text` フィールドは BM25 ハイブリッド検索に必要。機密データの場合はフルテキスト登録の要否を検討。

### 暗号化とネットワーク

- Azure AI Search はデフォルトで保存データを SSE (Service-managed key) で暗号化。
- CMK (Customer Managed Key) が必要な場合は [カスタマーマネージドキー](https://learn.microsoft.com/azure/search/search-security-manage-encryption-keys) を設定。
- 本番環境では **プライベートエンドポイント** の使用を推奨。

### RBAC (最小権限)

| ロール | 用途 |
|---|---|
| Search Service Contributor | インデックス作成・管理 |
| Search Index Data Contributor | ドキュメントのアップロード・更新 |
| Search Index Data Reader | 検索のみ (読み取り) |
| Cognitive Services OpenAI User | 埋め込み API 呼び出し |

アプリケーションには **Search Index Data Reader** + **Cognitive Services OpenAI User** のみを付与。
インデックス管理は CI/CD パイプラインに分離。

### データ保持・削除

```bash
# インデックス内の特定ドキュメント削除
az rest --method post \
    --url "https://<search>.search.windows.net/indexes/<index>/docs/index?api-version=2026-04-01" \
    --body '{"value":[{"@search.action":"delete","id":"<doc_id>"}]}'

# インデックス全体の削除
az search index delete --service-name <name> --name <index> --resource-group <rg> --yes
```

データ主体削除要求 (GDPR 等) に対応するため、`id` フィールドから元データとの
マッピングを管理し、削除ワークフローを文書化してください。

### Azure OpenAI の処理場所

- **Standard デプロイメント**: データはデプロイリージョンで処理。
- **Global Standard デプロイメント**: データは Microsoft のグローバルインフラで処理される場合あり。
- データの居住要件がある場合は Standard デプロイメントを選択。
- 詳細: [Azure OpenAI データ、プライバシー、セキュリティ](https://learn.microsoft.com/legal/cognitive-services/openai/data-privacy)

## Embedding の言語バイアス

- text-embedding-3-large は **英語データ主体**で学習。
- 英語文の分離度 > 他言語 (少数言語ほど精度低下)。
- **アラビア語、スワヒリ語、日本古語、ヨルバ語、ウォロフ語、ウイグル語などは cross-lingual 性能が明らかに落ちる**。
- 対策: 対象分野のペアデータで自作モデルを fine-tune (高難度)。`src/evaluate.py` で per-language 評価を実施。

## 意味の非対称性

- 「侘び寂び」「もののあはれ」→ 対応する英語概念なし → 英語コーパスでは弱ヒット。
- 「Enlightenment」→ 日本語「啓蒙」に対応するが、宗教的意味 (悟り) にもかかる → 混同。
- **翻訳可能性の限界を検索精度が反映**する。

## 検索結果の見せ方

- 「AI が選んだ」ということでの過信・権威化に注意。
- 常に **top-k 全部を人間が確認** する運用 (rerank 段階)。
- スコア絶対値だけで自動フィルタしない。

## 著作権と embedding

- **入力テキスト**は Azure OpenAI の学習に使われない (Azure 製品条項)。
- **著作権のあるテキストを embedding→保存**する場合、その embedding 自体の複製権解釈は法的にグレー。
- 商用サービスに載せる場合は権利者と協議。

## 保存ベクトルからの原文復元

- text-embedding-3-large は 3072 次元、原文の完全復元は困難。
- ただし **意味情報は多く保持**、embedding leak から機微内容が推測可能な研究あり。
- 機密文書は embedding も暗号化保存推奨。

## デジタル人文学における批判

- 「類似度検索」が **深い解釈** の代替と見なされる懸念。
- スコアが低い / 検索でヒットしない文献も**理論的価値**を持ちうる。
- AI 検索は **候補提示ツール**、判断は研究者に残る。

## 参考

- Kellner, M. (2023). *"The Limits of Multilingual Embeddings for Low-Resource Languages"*, ACL Workshop
- 日本デジタル・ヒューマニティーズ学会「AI と研究倫理」ガイドライン
- [Microsoft Responsible AI Standard](https://www.microsoft.com/ai/responsible-ai)
