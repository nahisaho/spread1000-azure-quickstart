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

`graphrag index` 実行前に `--dry-run` はないが、以下で概算:
- 文書総トークン数 × 平均 3-5 回 (extract + summarize + report) × モデル単価
- gpt-4o-mini (入力 $0.15/1M, 出力 $0.60/1M)
- text-embedding-3-small ($0.02/1M)

### 実行中モニタリング

Azure Portal → Cost Management → 対象サブスクリプション → 「今日のコスト」

過去 24 時間の Azure OpenAI 支出をリアルタイム確認可能 (更新に 8-24 時間ラグあり)。

### 予算アラート設定

```bash
az consumption budget create-with-rg \
    --resource-group rg-graphrag-quickstart \
    --budget-name "graphrag-monthly" \
    --amount 20 \
    --time-grain Monthly \
    --time-period start-date=$(date +%Y-%m-01)
```

$20/月を超えると通知メールが飛ぶ。

## 大規模インデックスの中断復旧

`graphrag index` は途中停止するとキャッシュ (`ragtest/cache/`) が残り、再実行時にスキップされます。**キャッシュを消すと最初から** LLM 課金がやり直しになるので注意。

## モデル切替でのコスト削減

- **試行段階**: gpt-4o-mini (安価、10-30% 精度低下)
- **本番運用**: gpt-4o (高精度、10-20 倍のコスト)
- **Embedding**: text-embedding-3-small のままで十分 (large にする必要性は低い)
