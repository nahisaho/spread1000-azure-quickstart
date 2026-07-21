# 02. AML workspace + A100 compute プロビジョニング

## 0. 前提

- [01. 前提条件](01-prerequisites.md) を完了していること
- サブスクリプションを選択済み、GPU quota 24+ 確保済み

環境変数の再確認:

```bash
echo "SUB: $AZURE_SUBSCRIPTION_ID"
echo "LOC: $AZURE_LOCATION"
echo "RG:  $AZURE_RESOURCE_GROUP"
```

## 1. Bicep で workspace 一式をデプロイ (5〜10 分)

```bash
cd research-fields/life-pharma-science/05-conformational-ensemble-bioemu
bash infra/deploy.sh
```

このスクリプトが作成するリソース:

| リソース | 用途 |
|---|---|
| Resource Group `rg-spread1000-bioemu` | 全リソースの親 |
| Storage Account `stbioemu<suffix>` (LRS) | workspaceblobstore + Job I/O |
| Key Vault `kv-bioemu-<suffix>` | AML の secret 保管 (RBAC 認可) |
| Log Analytics `log-bioemu-<suffix>` | App Insights のバックエンド |
| Application Insights `appi-bioemu-<suffix>` | workspace-based |
| AML Workspace `mlw-bioemu-<suffix>` | 中心リソース |

完了時の出力例:

```
==== デプロイ完了 ====
  Workspace:       mlw-bioemu-a1b2c3
  Storage Account: stbioemua1b2c3
  Key Vault:       kv-bioemu-a1b2c3
```

出力に従って環境変数を設定:

```bash
export AZURE_RESOURCE_GROUP=rg-spread1000-bioemu
export AZURE_WORKSPACE_NAME=mlw-bioemu-a1b2c3    # ← 実際の名前
export AZURE_STORAGE_ACCOUNT=stbioemua1b2c3      # ← 実際の名前

az configure --defaults \
  group="$AZURE_RESOURCE_GROUP" \
  workspace="$AZURE_WORKSPACE_NAME"
```

> [!TIP]
> `deploy.sh` は subscription-scope デプロイなので、既存の RG があっても衝突しません。同じ RG に対して再実行するとリソース名 (suffix) が同じになるため冪等です。

## 2. AML CLI で workspace を確認

```bash
az ml workspace show \
  --name "$AZURE_WORKSPACE_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --query "{name:name, location:location, provisioningState:provisioning_state}" \
  -o jsonc
```

`provisioningState: "Succeeded"` を確認。

## 3. Custom Environment (bioemu 1.4.1) をビルド

BioEmu は PyTorch + JAX + TensorFlow-CPU + AlphaFold + PyTorch Geometric という重い組み合わせなので、AML curated environment では要件を満たせません。カスタム Docker イメージを AML 上でビルドします (10〜20 分)。

```bash
cd aml
az ml environment create --file environment.yml
cd ..
```

進捗は AML Studio → Environments → `bioemu-1-4-1-cuda` → Build logs で確認できます。**Build succeeded** の表示を待ちます。

> [!IMPORTANT]
> 初回ビルドは `bioemu[cuda]` の依存 (JAX cuda12, PyTorch 2.6+ etc.) をダウンロード・インストールするため 15〜25 分かかることがあります。**Job を投げる前に必ず build を完了**させてください。

## 4. A100 compute (Spot) を作成

```bash
az ml compute create --file aml/compute-a100.yml
```

**Spot (`tier: low_priority`)** を推奨:

- PAYG ¥799/h → Spot ¥148/h (約 80% 削減)
- BioEmu は独立サンプリングなので中断してもやり直せる
- `min_instances: 0` により、Job が終わると自動で 0 ノードに縮小 (課金停止)

> [!NOTE]
> Spot でノード確保できない場合 (供給不足) は `aml/compute-a100.yml` の `tier: low_priority` を `tier: dedicated` に変更して再作成してください。

確認:

```bash
az ml compute show --name gpu-a100 \
  --query "{name:name, size:size, state:provisioning_state, min:min_instances, max:max_instances, idle:idle_time_before_scale_down}" \
  -o jsonc
```

`state: "Succeeded"` を確認。この時点ではノード数 0 なので課金なし。

## 5. GPU が本当に使えるか smoke test (任意, ~5 分)

一度だけ小さな検証 Job を投げて A100 が確保できることを確認:

```bash
az ml job create --file aml/gpu-smoke-test.yml --stream
```

出力に `NVIDIA A100 80GB PCIe` が見えれば OK。**Spot で確保できない場合は数分〜数十分キューに残る**ことがあります。

## 6. コスト管理の再確認

```bash
az ml compute show --name gpu-a100 --query "current_node_count" -o tsv
# → 0 が期待値 (idle_time_before_scale_down 経過後)
```

Job 完了後は必ずここが 0 になることを [`05-cleanup.md`](05-cleanup.md) の手順で毎回確認してください。

## チェックリスト

- [ ] `az ml workspace show` が `Succeeded` を返す
- [ ] AML Studio Environments で `bioemu-1-4-1-cuda:1` が **Build succeeded**
- [ ] `az ml compute show` で `state: Succeeded`, `min_instances: 0`
- [ ] smoke test で A100 が確保できた (任意)

## 次のステップ

→ [03. Chignolin 100 サンプル生成 (Job 実行)](03-run-bioemu.md)
