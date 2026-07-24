# 05 — クリーンアップ

## 環境変数を再読み込み

新しいシェルで作業する場合：

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/social-science/02-document-structuring"
cd "$SCENARIO_DIR"
set -a; source .env; set +a
```

## Doc Intelligence / AOAI は「起動中課金」がありません

両リソースとも**存在するだけでは無課金**（ページ / トークン使用のみ課金）。したがって「停止」の概念はありません。使い終わったら **リソースグループごと削除** するのが最も簡単です。

## リソースグループを削除

```bash
az resource list -g "$DOC_RG" -o table

az group delete -n "$DOC_RG" --yes --no-wait
```

- 完全削除まで **5〜10 分**
- Document Intelligence アカウント / Azure OpenAI が消えます

## AOAI モデルデプロイのみ削除したい場合

Bicep インフラは残してモデルデプロイだけ消すには：

```bash
az cognitiveservices account deployment delete \
  -g "$DOC_RG" \
  -n "$AOAI_ACCOUNT_NAME" \
  --deployment-name "$AOAI_DEPLOYMENT_NAME"
```

## 論理削除

Cognitive Services アカウント (Doc Intelligence / AOAI) を削除すると通常 **48 時間の論理削除保持** があります。同名で再作成する場合は待つか、次で完全削除：

```bash
az cognitiveservices account purge \
  -g "$DOC_RG" -n "$AOAI_ACCOUNT_NAME" -l japaneast

az cognitiveservices account purge \
  -g "$DOC_RG" -n "$DOC_INTEL_NAME" -l japaneast
```

## 削除確認

```bash
az group show -n "$DOC_RG" 2>&1 | grep -i "not found" && \
  echo "✓ Resource group deleted" || echo "⏳ still deleting..."
```

## ローカル成果物

以下はデータプライバシー・研究再現性のため、公開レポジトリに含めないでください：

- `.env` (エンドポイント、デプロイ名)
- `data/*.pdf` (実文書を使った場合)
- `data/output/*` (抽出結果と Markdown 中間出力)

## コスト予算アラート (ワークショップ前の推奨)

ワークショップ開始前に $10 の予算アラートを設定しておくと安心です：

```bash
az consumption budget create \
  --budget-name "spread-social-02-workshop" \
  --amount 10 \
  --time-grain Monthly \
  --resource-group "$DOC_RG" \
  --category Cost \
  --start-date "$(date +%Y-%m-01)" \
  --end-date "$(date -d '+6 months' +%Y-%m-01)"
```

## コストの最終確認

Azure Portal → **Cost Management** → **コスト分析** → リソースグループ = `$DOC_RG`

> [!NOTE]
> コスト分析への反映は最大 8-24 時間遅延します。ワークショップ終了直後にコストが $0 に見えても正常です。
