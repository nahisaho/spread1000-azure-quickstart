# 06 — 片付けとコスト管理

## Azure リソースの削除

チュートリアルで作ったリソース グループを丸ごと削除:
```bash
az group delete -n rg-graphrag-quickstart --yes --no-wait
```

## ローカル成果物の削除

```bash
rm -rf ragtest/
rm -rf outputs/
deactivate && rm -rf .venv
```

**注意**: `.env` は削除する前にキーをローテートするか、`chmod 600 .env` で保護。

## コスト監視

### 事前見積り

- `bash src/run.sh` は index 実行前にコーパスサイズを推定して警告する仕組みを内蔵 (デフォルト上限 $10)。上限を超えると停止 → `GRAPHRAG_BUDGET_USD=50 bash src/run.sh` で明示的に緩和。
- **preflight 検証**: `python -m graphrag index --root ./ragtest --dry-run` で LLM 呼び出しなしに設定を検証できる (`run.sh` 内で自動実行)。
- 手動概算式: 総トークン数 × 3-5 (extract + summarize + report) × モデル単価。gpt-4o-mini は入力 $0.15/1M、出力 $0.60/1M、text-embedding-3-small は $0.02/1M。

### 実行中モニタリング

Azure Portal → Cost Management → 対象サブスクリプション → 「今日のコスト」

過去 24 時間の Azure OpenAI 支出をリアルタイム確認可能 (更新に 8-24 時間ラグあり)。

### 予算アラート設定 (**遅延通知のみ、ハードキャップではない**)

Azure 予算は通知のみで、超過時に自動停止しません。有意な保護には Azure Cost Management → Budget → **Action Group** (Web Hook で Function を呼びリソースをロック) が必要。以下は通知先つきの最小例:

```bash
EMAIL="you@example.com"
az consumption budget create \
    --budget-name "graphrag-monthly" \
    --amount 20 \
    --time-grain Monthly \
    --category Cost \
    --start-date "$(date +%Y-%m-01)" \
    --end-date "$(date -d '+12 months' +%Y-%m-01)" \
    --notifications 'notification1={"operator":"GreaterThan","threshold":80,"contactEmails":["'"$EMAIL"$'"],"enabled":true}'
```

`az consumption budget create-with-rg` は **notifications 引数を受け付けない古い CLI サブコマンド**なので、上記のように `az consumption budget create` + `--notifications` を使ってください (CLI 拡張 `costmanagement` が必要な場合あり)。

## 大規模インデックスの中断復旧

`graphrag index` は途中停止するとキャッシュ (`ragtest/cache/`) が残り、再実行時にスキップされます。**キャッシュを消すと最初から** LLM 課金がやり直しになるので注意。

## モデル切替でのコスト削減

- **試行段階**: gpt-4o-mini (安価、10-30% 精度低下)
- **本番運用**: gpt-4o (高精度、10-20 倍のコスト)
- **Embedding**: text-embedding-3-small のままで十分 (large にする必要性は低い)
