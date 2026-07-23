# トラブルシューティング

## デプロイ

### `deploy.sh` が `AuthorizationFailed` で止まる
Bicep が RoleAssignment を作成する権限は **Owner** または **User Access Administrator** が必要です。

### `SpecialFeatureOrQuotaIdRequired` (AOAI 未申請)
<https://aka.ms/oai/access> で利用申請してください。

### `The subresource 'FormRecognizer' is not available in region 'japaneast'`
Document Intelligence は `kind: FormRecognizer` として内部管理されていますが、Japan East で利用可能です。エラーが出た場合は Provider 登録漏れの可能性: `az provider register --namespace Microsoft.CognitiveServices --wait`

### `Model 'gpt-5.4-mini' version '2026-03-17' is not available`
[モデル利用可能性マトリックス](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability?pivots=standard) を確認し、`parameters.json` の `modelVersion` を更新してください。

## 認証

### `DefaultAzureCredential failed to retrieve a token`
- `az login` 済みか
- Cognitive Services User / Cognitive Services OpenAI User ロールが割り当て済みか
- ロール反映に最大 5 分かかります

### `401 PermissionDenied` (Document Intelligence 呼び出し)
Doc Intelligence 側は `Cognitive Services User` ロール (`a97b65f3-24c7-4388-baec-2e87135dc908`) が必要です。`Contributor` だけではデータプレーンの `begin_analyze_document` は呼べません。

### `401 PermissionDenied` (Azure OpenAI 呼び出し)
AOAI 側は `Cognitive Services OpenAI User` ロール (`5e0bd9bd-7b93-4f28-af87-19fc36ad61bd`) が必要です。

## 抽出 (extract.py)

### `AttributeError: module 'openai' has no attribute 'beta'`
`openai>=1.50.0` が必要です。`pip install --upgrade openai` してください。

### `response_format` エラー / Structured Outputs strict mode failure
Pydantic モデルの全フィールドを **required + nullable** で定義してください。`str | None` はOK。`Optional[str] = None` (デフォルト値付き) は strict モードで rejects されることがあります。

### `content_filter` refusal
公式判例など内容によっては Azure OpenAI コンテンツフィルタが反応することがあります。ログの `refusal` フィールドを確認してください。

### `429 Too Many Requests`
gpt-5.4-mini Standard の TPM/RPM 上限に達しています。`--concurrency` を減らすか、`infra/parameters.json` の `aoaiDeploymentCapacity` を上げてください（既定 10 → 30 等）。

### 抽出結果が空 / null が多い
- 元 PDF の OCR 品質が悪い可能性 → `data/output/*.markdown.txt` を目視確認
- LLM に渡した Markdown 全文をログに残す (`--debug` オプション)
- スキーマが実文書と合っていない可能性

### 表が分割されて抽出される
Document Intelligence では複数ページに跨る表は別 `table` オブジェクトになる場合があります。列数と `bounding_regions.page_number` で結合してください。参考: [Cross-page table merge sample](https://github.com/Azure-Samples/document-intelligence-code-samples/blob/main/Python%28v4.0%29/Retrieval_Augmented_Generation_%28RAG%29_samples/sample_identify_and_merge_cross_page_tables.py)

## PDF 生成 (generate_demo_pdfs.py)

### `ModuleNotFoundError: No module named 'reportlab'`
```bash
pip install "reportlab>=4.0.0"
```

### 日本語が □□□ になる (tofu)
本スクリプトは Noto Sans JP CJK フォント (matplotlib 同梱) を利用します。`pip install matplotlib>=3.8.0` を確認してください。それでも欠ける場合は `--font-path` で OS フォントを指定してください。

## クリーンアップ

### `az group delete` に時間がかかる
Doc Intelligence / AOAI の削除には数分かかります。`--no-wait` で開始し、`az group show -n $RG` で完了確認してください。

### 削除後もコストが発生している
Log Analytics の**論理削除保持** (90 日) がありますが追加課金はありません。もしトークン / ページ料金が残っている場合、削除前の呼び出し分です。
