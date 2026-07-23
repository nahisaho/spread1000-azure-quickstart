# トラブルシューティング

## 認証

### `DefaultAzureCredential failed to retrieve a token`

- `az login` を実行し、対象サブスクリプションを選択
- Cloud Shell では既にログイン済み
- Bicep デプロイで自分に `Cognitive Services OpenAI User` ロールを付与したか確認 (`infra/main.bicep` が自動付与)

### `AuthenticationError: Bearer token used but disableLocalAuth is true`

- キー認証を無効化しているため、`api_key="..."` を渡さないでください
- `openai.OpenAI(api_key=token_provider)` の `api_key` は**callable** (bearer token provider) を渡します

## デプロイ

### `Deployment failed: The model 'text-embedding-3-small' is not available in region 'swedencentral' as Regional`

- Sweden Central は Regional Standard の small を提供していません
- Japan East または East US 2 を選ぶか、GlobalStandard デプロイに切り替え

### `Cognitive Services account name must be 2-64 characters`

- `aoaiAccountName` はグローバル一意 (2〜64 文字、小文字英数字とハイフン)
- 既定値は `aoai-social-03-<hash>` (`uniqueString(resourceGroup().id)`) で名前衝突を回避します。固定名にしたい場合は `parameters.json` の `aoaiAccountName` を指定

## Embeddings

### `BadRequestError: This model's maximum context length is 8192 tokens`

- 1 入力あたり最大 8,192 tokens
- 長文は事前に分割 (`src/embed.py --max-chars 4000` などで抑制可能)

### `TooManyRequestsError (429)` — レート超過

- 応答ヘッダー `retry-after-ms` を確認
- `src/embed.py` は 5 回まで指数バックオフ + jitter で再試行
- 割当 TPM を確認: `az cognitiveservices account deployment show`

## 分類

### `ValueError: n_splits=5 cannot be greater than the number of members in each class`

- 各ラベル最低 5 件必要 (StratifiedKFold の要件)
- 合成データを増やすか `--n-splits 3` に下げる

### macro-F1 が 0.5 前後

- 60 件規模では偶然の分散が大きいです
- クラス間の分布不均衡を `classification_report` の support 列で確認
- 埋め込みモデルを `text-embedding-3-large` に変えて再計測

## クラスタリング

### 全てのテキストが 1 クラスタに集約される

- L2 正規化を忘れているか確認 (`src/cluster.py` は既定で実施)
- テキスト集合が意味的に近すぎる可能性。`--k-range` を 2 から広げて silhouette を確認

### UMAP が「too few neighbors」と警告

- 30 件未満のデータでは UMAP の既定 `n_neighbors=15` が過大
- [docs/05-cluster.md](docs/05-cluster.md) の UMAP サンプルコードでは `umap.UMAP(n_neighbors=5, ...)` のように縮小してください
