# 05 — クリーンアップ

## コンピュートを停止 (課金停止)

`min_instances: 0` に設定済みなので、アイドル 120 秒で自動的にノード数が 0 になります。**ノード数 0 の間、VM 課金は発生しません**。

明示的に確認したい場合：

```bash
az ml compute list --query "[].{name:name, currentNodeCount:current_node_count}" -o table
```

`currentNodeCount = 0` を確認できれば OK。

> [!NOTE]
> `az ml compute update --max-instances 0` は AML CLI の仕様上受け付けません (最小値は 1)。`min_instances: 0` (デフォルト) のままで課金は停止します。完全に削除するなら `az ml compute delete -n gpu-cluster -y`。

## ACR Basic は削除しないと課金継続

Azure Container Registry (Basic) は約 **$5/月** の固定課金です。1 回試して終わりなら **リソースグループごと削除**が最速です。

## リソースグループを削除 (最速・全消し)

```bash
# 消える対象を最終確認
az resource list -g spread-chem-react-rg -o table

# 実行 (--yes 付きだとプロンプト無し)
az group delete -n spread-chem-react-rg --yes --no-wait
```

- 完全削除まで **10〜20 分**
- Storage / Key Vault / Log Analytics / App Insights / ACR / Workspace / Compute 全てが消えます
- Key Vault と Log Analytics は**論理削除保持期間**（90 日程度）を残しますが、追加課金はありません

## 削除確認

```bash
az group show -n spread-chem-react-rg 2>&1 | grep -i "not found" && \
  echo "✓ Resource group deleted" || echo "⏳ still deleting..."
```

## デフォルト設定の解除

```bash
az configure --defaults group="" workspace=""
```

## コストの最終確認

Azure Portal → **Cost Management + Billing** → **コスト分析** → スコープを本サブスクリプションに、フィルタで **リソースグループ = spread-chem-react-rg** を指定すると、この試行の合計コストが確認できます。**$1 以下**に収まっていれば想定通りです。
