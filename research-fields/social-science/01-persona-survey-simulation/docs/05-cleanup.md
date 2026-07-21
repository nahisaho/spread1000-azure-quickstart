# 05 — クリーンアップ

## 環境変数を再読み込み

新しいシェルで作業する場合は、[`docs/02-provision-aoai.md`](02-provision-aoai.md) で保存した `.env` を再読み込みします：

```bash
cd research-fields/social-science/01-persona-survey-simulation
set -a; source .env; set +a
# もし .env が無い / 失った場合は手動で設定:
# export AOAI_RG=spread-social-rg
# export AOAI_ACCOUNT_NAME=aoai-spread-social-01
# export AOAI_DEPLOYMENT_NAME=survey-gpt41mini
```

## Azure OpenAI は「起動中課金」がありません

Azure OpenAI リソースは**存在するだけでは無課金**で、トークン使用量のみが課金されます。したがって「停止」の概念はありません。使い終わったら **リソースグループごと削除** するのが最も簡単です。

## リソースグループを削除

```bash
# 消える対象を最終確認
az resource list -g "$AOAI_RG" -o table

# 削除実行
az group delete -n "$AOAI_RG" --yes --no-wait
```

- 完全削除まで **5〜10 分**
- Azure OpenAI アカウント / Log Analytics / App Insights が消えます

## AOAI モデルデプロイのみ削除したい場合

Bicep インフラは残したままモデルデプロイだけ消すには：

```bash
az cognitiveservices account deployment delete \
  -g "$AOAI_RG" \
  -n "$AOAI_ACCOUNT_NAME" \
  --deployment-name "$AOAI_DEPLOYMENT_NAME"
```

モデルデプロイを削除すると新規推論はできませんが、AOAI アカウント自体は課金なしで残ります。

## Azure OpenAI の「論理削除」

Azure OpenAI アカウントを削除すると、通常 **48 時間の論理削除保持期間** があります。同名で再作成する場合は待つか、次で完全削除：

```bash
az cognitiveservices account purge \
  -g "$AOAI_RG" \
  -n "$AOAI_ACCOUNT_NAME" \
  -l japaneast
```

## 削除確認

```bash
az group show -n "$AOAI_RG" 2>&1 | grep -i "not found" && \
  echo "✓ Resource group deleted" || echo "⏳ still deleting..."
```

## `.env` とローカル成果物

以下のファイルには API エンドポイントや実験結果が含まれます。研究データとして保存する場合はプライベートストレージに移し、公開レポジトリには含めないでください：

- `.env` (エンドポイント、デプロイ名)
- `data/responses.csv` (シミュレーション結果)
- `data/analysis/*` (統計結果)

## コストの最終確認

Azure Portal → **Cost Management + Billing** → **コスト分析** → フィルタで **リソースグループ = `$AOAI_RG`** を指定すると、この試行の合計コストが確認できます。**$0.10 以下**に収まっていれば想定通りです。
