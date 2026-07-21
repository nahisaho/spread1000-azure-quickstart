# 01. コスト管理

> **対象読者**: SPReAD-1000 採択の研究代表者（Azure 未経験）
> **所要時間**: 初回 60 分 + 週次 15 分の確認
> **前提**: [`00-azure-account-setup.md`](00-azure-account-setup.md) を完了していること

このドキュメントは **「気がついたら数十万円請求されていた」を防ぐ** ための実践ガイドです。Azure のコストは秒単位で発生します。特に GPU / HPC は 1 時間放置しただけで数千円になるため、**予算アラートは必ず設定**してください。

---

## 1. Azure コストの構造を理解する

Azure の請求は以下 4 種類の合計です。

| 項目 | 課金単位 | SPReAD-1000 で高額になりやすい例 |
|---|---|---|
| **Compute** | 秒 or 時間（VM 稼働中のみ） | GPU VM（A100 / H100）、AML compute |
| **Storage** | GB 月・トランザクション数 | 大容量データセット、Data Lake、AML アーティファクト |
| **Network** | GB（**インターネット向け egress で課金**。同一リージョン内・受信は原則無料だが、リージョン間・ゾーン間転送や一部サービス経由の egress は課金対象） | サンプル出力を大量ダウンロード、リージョン跨ぎのデータ移動 |
| **PaaS 固有** | サービス依存 | Azure OpenAI トークン、Batch ジョブ、Container Registry ストレージ |

> [!IMPORTANT]
> **VM を「停止」しただけでは課金は止まりません。** Azure Portal の VM 画面で `Stop (deallocate)` を選ぶか、CLI で `az vm deallocate` を実行して初めて Compute 課金が止まります。ゲスト OS を shutdown しただけでは停止扱いになりません（後述 3.3）。

---

## 2. 予算アラート（Budget）の設定 — **最優先タスク**

**最悪でも設定すべきは「サブスクリプション単位の月額予算」** です。閾値を超えるとメールで通知され、自動でリソースを止めることも可能です。

### 2.1 ポータルから設定（初心者向け）

1. Azure Portal → **Cost Management + Billing** → **Cost Management** → **Budgets**
2. **Add** → 名前・期間（月次推奨）・金額（例: ¥100,000）を入力
3. アラート条件を追加:
   - **Actual 80%** → メール通知
   - **Actual 100%** → メール通知 + Action Group で自動停止
   - **Forecasted 100%** → 予測ベースの早期警告

### 2.2 Bicep で設定（クイックスタート標準）

このリポジトリには再利用可能なテンプレートが用意されています: **[`shared/bicep-modules/budget.bicep`](../shared/bicep-modules/budget.bicep)**

```bicep
targetScope = 'subscription'

@description('Budget name')
param budgetName string = 'spread1000-monthly'

@description('Monthly budget amount (in the billing currency of the subscription)')
param amount int = 100000

@description('Alert email addresses')
param alertEmails array = [
  'pi@example.ac.jp'
]

// 現在の月の 1 日を自動設定（毎回デプロイ時に更新される）
@description('First day of the current month, yyyy-MM-01')
param startDate string = utcNow('yyyy-MM-01')

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: {
      Actual_80_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 80
        thresholdType: 'Actual'
        contactEmails: alertEmails
      }
      Actual_100_Percent: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        thresholdType: 'Actual'
        contactEmails: alertEmails
      }
      Forecasted_100_Percent: {
        enabled: true
        operator: 'GreaterThan'
        threshold: 100
        thresholdType: 'Forecasted'
        contactEmails: alertEmails
      }
    }
  }
}
```

> [!NOTE]
> `startDate` は「月次予算の初回集計開始日」で、**その月の 1 日**である必要があります。既定値 `utcNow('yyyy-MM-01')` は初回デプロイ時に現在月の 1 日を設定します。
>
> **⚠️ 重要**: **一度作成した budget の `startDate` は変更できません**（Azure API の制約）。予算金額やアラート閾値のみを変更する再デプロイなら問題ありませんが、**別月に再デプロイする場合は元の `startDate` を明示的にパラメータで渡す**必要があります:
>
> ```bash
> az deployment sub create \
>   --location japaneast \
>   --template-file shared/bicep-modules/budget.bicep \
>   --parameters startDate=2026-08-01 amount=150000
> ```
>
> `startDate` そのものを別月に変えたい場合は、`az consumption budget delete --budget-name spread1000-monthly` で削除してから再作成してください。

デプロイ:

```bash
az deployment sub create \
  --location japaneast \
  --template-file shared/bicep-modules/budget.bicep \
  --parameters alertEmails="['pi@example.ac.jp']"
```

> [!WARNING]
> **予算アラートはあくまで「通知」であり、課金を自動的に止めるものではありません。** 自動停止させるには Action Group + Logic App / Automation Runbook で `az vm deallocate` を実行するワークフローを組む必要があります。まずは通知だけでも設定し、届いたら手動でリソースを停止する運用を推奨します。

### 2.3 予算金額の目安（初回）

| 用途 | 推奨予算 / 月 | 根拠 |
|---|---:|---|
| クイックスタート試用のみ | ¥30,000 | GPU VM を数時間、AML compute で数ジョブ |
| 単一シナリオを本格運用 | ¥100,000〜¥300,000 | A100 週 40 時間、Storage 1TB |
| 複数シナリオ + 保存データ | ¥500,000〜 | H100 + 中規模データ + 長期保存 |

---

## 3. 主要な課金の止め方（緊急停止レシピ）

### 3.1 リソースグループごと削除（**推奨・最も確実**）

**各クイックスタートの `99-cleanup` が採用している方法です。**

```bash
RG="spread1000-example"     # ← 自分のシナリオ名に置き換える
az group delete --name "$RG" --yes --no-wait
```

**注意**: `--no-wait` は削除を非同期実行します。完了確認は:

```bash
az group show --name "$RG" --query properties.provisioningState -o tsv 2>/dev/null || echo "Deleted"
```

### 3.2 VM を停止（データを残したい場合）

```bash
RG="spread1000-example"
VM_NAME="vm-example"

# VM 停止（課金停止）
az vm deallocate --resource-group "$RG" --name "$VM_NAME"

# 状態確認: PowerState が "VM deallocated" になっていれば OK
az vm show --resource-group "$RG" --name "$VM_NAME" --show-details \
  --query "{name:name, power:powerState}" -o table
```

### 3.3 「停止」と「割り当て解除」の違い（要注意）

| 操作 | Compute 課金 | Storage 課金 | 用途 |
|---|---|---|---|
| ゲスト OS で `shutdown -h now` | **継続** ⚠️ | 継続 | ❌ Azure から見ると VM は「起動中」扱いで課金が続く |
| `az vm stop`（既定動作） | **継続** ⚠️ | 継続 | ❌ ハイパーバイザで停止するだけ、ホストを予約したままで課金継続 |
| Azure Portal の **Stop** ボタン | 停止 ✅ | 継続 | 一時停止（GUI、既定で `Stop (Deallocate)` 相当を実行） |
| `az vm deallocate` | 停止 ✅ | 継続（ディスク分） | 一時停止（CLI、明示的に deallocate） |
| `az group delete` | 停止 ✅ | 停止 ✅ | 完全撤去 |

> [!IMPORTANT]
> - **Azure Portal の「Stop」ボタンは現在の UI では割り当て解除（deallocate）を実行**します。ただし CLI の `az vm stop` は割り当て解除しない「stopped」状態を作るだけで課金は続きます。**課金を止めたい場合は必ず `az vm deallocate` を使ってください。**
> - **ゲスト OS 内での `shutdown`（Linux/Windows いずれも）は Azure から見ると停止扱いにならず課金が続きます。**必ず Portal または CLI 経由で停止してください。

### 3.4 AML compute を停止

```bash
RG="spread1000-example"
WS="spread1000-example-ws"
CI_NAME="ci-example"           # compute instance
CLUSTER_NAME="gpu-a100-cluster"

# コンピュートインスタンス（対話用）
az ml compute stop --name "$CI_NAME" \
  --resource-group "$RG" --workspace-name "$WS"

# コンピュートクラスター（バッチ用）: min-instances=0 なら自動でスケールダウン
az ml compute update --name "$CLUSTER_NAME" \
  --resource-group "$RG" --workspace-name "$WS" \
  --min-instances 0
```

### 3.5 自動シャットダウン（Auto-shutdown）

VM 単体には Portal から「毎日 19:00 に自動停止」を設定できます。**AML コンピュートインスタンスにはアイドル時停止（Idle shutdown）** を必ず設定してください。

```bash
RG="spread1000-example"
WS="spread1000-example-ws"

# コンピュートインスタンス作成時に 60 分アイドルで自動停止
az ml compute create \
  --file compute-instance.yml \
  --resource-group "$RG" --workspace-name "$WS" \
  --set idle_time_before_shutdown_minutes=60
```

---

## 4. タグ戦略（コスト分析の前提）

タグを付けないと「どのシナリオがいくら使っているか」が分かりません。**各クイックスタートは以下 3 タグを最低限付与**します。

| タグキー | 値の例 | 用途 |
|---|---|---|
| `project` | `spread1000` | プロジェクト単位で集計 |
| `scenario` | `alphafold3` / `bioemu` / `monai` | シナリオ別コスト |
| `pi` | `yamada-taro` | 研究代表者別（複数 PI で 1 サブスク共有時） |

### 4.1 RG 作成時にタグを付与

```bash
az group create \
  --name spread1000-alphafold3 \
  --location japaneast \
  --tags project=spread1000 scenario=alphafold3 pi=yamada-taro
```

### 4.2 タグ強制（Azure Policy）

サブスクリプション全体で「タグの無い RG は作成禁止」にできます:

```bash
az policy assignment create \
  --name require-project-tag \
  --policy /providers/Microsoft.Authorization/policyDefinitions/96670d01-0a4d-4649-9c89-2d3abc0a5025 \
  --params '{"tagName":{"value":"project"}}' \
  --scope "/subscriptions/$(az account show --query id -o tsv)"
```

---

## 5. Cost Analysis の見方

Azure Portal → **Cost Management** → **Cost analysis** で、以下の切り口が有効です。

| ビュー | 用途 |
|---|---|
| Accumulated cost | 月次の累積コスト推移（予算に対する進捗） |
| Daily costs | 日次の変動（急増を検出） |
| Cost by resource | どのリソースが高いか |
| Cost by tag | どのシナリオが高いか（タグ運用時） |
| Cost by service | Compute / Storage / Network の内訳 |

CLI で日次コストを取得（**Bash / WSL / Linux 前提**。macOS の BSD `date` や Windows PowerShell では日付形式のオプションが異なるため、下記の `date -d` は動きません。macOS では `date -v-30d +%Y-%m-%d`、PowerShell では `(Get-Date).AddDays(-30).ToString('yyyy-MM-dd')` に置き換えてください）:

```bash
az consumption usage list \
  --start-date $(date -d '30 days ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --query "[?tags.scenario=='alphafold3'].{date:usageStart, service:consumedService, cost:pretaxCost}" \
  -o table
```

> [!NOTE]
> Cost データはリアルタイムではなく **8〜24 時間遅延**します。GPU を回した直後に確認しても反映されていないので、翌日にチェックする運用にしてください。

---

## 6. GPU / HPC 特有のコスト最適化

### 6.1 Spot VM（低優先度）で最大 90% 割引

学習・推論・大規模計算は Spot で十分な場合が多いです。

| SKU (Japan East) | PAYG / 時 | Spot 目安 / 時 | 削減率 |
|---|---:|---:|---:|
| NC24ads_A100_v4 | ~$5.33 | ~$0.98 | 82% |
| NC40ads_H100_v5 | ~$10.12 | ~$4.66 | 54% |
| NC48ads_A100_v4 | ~$10.65 | ~$1.97 | 82% |

> [!WARNING]
> **Spot は Azure 側の都合で強制退去（eviction）される** ため、チェックポイント保存が必須です。学習ジョブでは 10〜30 分ごとにチェックポイントを保存し、AML の `retry_settings` で再実行するようにします。

Spot 指定例（AML compute cluster）:

```yaml
# compute-a100-spot.yml
$schema: https://azuremlschemas.azureedge.net/latest/amlCompute.schema.json
name: gpu-a100-spot
type: amlcompute
size: Standard_NC24ads_A100_v4
min_instances: 0
max_instances: 4
tier: low_priority   # ← Spot（AML では low_priority 表記、他の SKU 指定文字列は "dedicated"）
idle_time_before_scale_down: 300
```

### 6.2 自動スケールダウン

AML コンピュートクラスターは `min_instances: 0` + `idle_time_before_scale_down: 300`（秒）を設定すれば、ジョブ終了 5 分後にゼロに戻ります。**必ず設定**してください。

### 6.3 Storage tier の使い分け

| Tier | GB/月コスト目安（JP East） | 最短保持期間 | 用途 |
|---|---:|---:|---|
| Hot | ¥3〜 | なし | アクティブな実験データ |
| Cool | ¥1.6〜 | 30 日 | 完了した実験の一次保管 |
| Cold | ¥0.6〜 | 90 日 | アーカイブ手前 |
| Archive | ¥0.15〜 | 180 日 | 論文投稿後の長期保管（読み出しに数時間） |

古いデータは Lifecycle Management で自動 tier 移行できます:

```bash
RG="spread1000-example"
STORAGE_ACCOUNT="stexamplespread1000"

az storage account management-policy create \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RG" \
  --policy @lifecycle-policy.json
```

### 6.4 Reserved Instance / Savings Plan

**3 ヶ月以上 24 時間常時稼働するリソースがある場合のみ**、1 年 / 3 年の予約購入で 30〜60% 割引になります。SPReAD-1000 のような期間限定研究では**多くの場合 Spot + PAYG の方が安い**ため、常時稼働の VM が固まってから検討してください。

### 6.5 Egress（送信）を減らす

- Storage / AML のリージョンは**必ず compute と同じリージョン**にする（別リージョンは inter-region egress 課金）
- 大量ダウンロードが必要なら **Storage の SAS URL でクライアント側から直接ダウンロード**（Azure→インターネット egress は同じだが、Compute VM のディスク I/O を経由しない分効率的）
- 論文用の最終アーティファクトのみダウンロードし、中間ファイルは Azure 上で保管

---

## 7. Azure Advisor でムダを検出

Azure Portal → **Advisor** → **Cost** タブに、以下の推奨が表示されます。

- 使われていない VM の停止推奨
- 使われていない Public IP / NIC / ディスク（**孤児リソース**）
- サイズ過剰な VM のリサイズ推奨
- Reserved Instance の購入シミュレーション

**週次で確認する運用**を推奨します。

---

## 8. 完了チェックリスト

- [ ] サブスクリプション単位の月次予算アラートを設定した（Section 2）
- [ ] 予算超過通知の受信先メールを機関のアドレスに設定した
- [ ] 各 RG に `project=spread1000` `scenario=<name>` タグを付ける運用にした
- [ ] `99-cleanup.sh` は各クイックスタート実行後に**必ず**流す運用を決めた
- [ ] GPU シナリオでは Spot + `min_instances: 0` を優先することを理解した
- [ ] Cost Analysis を週 1 回確認するルーティンを決めた
- [ ] 帰宅前・週末前に「今動いている VM 一覧」を確認するようにした:

```bash
az vm list --show-details --query "[?powerState!='VM deallocated'].{name:name, rg:resourceGroup, size:hardwareProfile.vmSize, power:powerState}" -o table
```

---

## 9. トラブルシューティング

| 症状 | 原因 | 対応 |
|---|---|---|
| 予算アラートが来ない | メール宛先ミス / 迷惑メール振分け | Budget の Contact Emails を再確認、`azure-noreply@microsoft.com` を許可 |
| Cost Analysis の数字が想定より高い | Storage / egress が見落とし | サービス別ビューで内訳確認 |
| RG 削除が失敗 | 削除ロック（`CanNotDelete`）が付いている | `az lock list --resource-group $RG` → `az lock delete` |
| 削除したはずのリソースがまだ課金 | 依存 RG（例: AML の Managed RG）が残存 | Portal で「削除可能なリソースグループ」を全て検索 |
| Spot VM が頻繁に evict される | リージョン需要が逼迫 | 別リージョン（East US 2、Sweden Central 等）を検討 |
| AML compute が停止しない | `min_instances` が 1 以上 | `az ml compute update --min-instances 0` |

---

## 参考リンク

- Azure 料金計算ツール: <https://azure.microsoft.com/ja-jp/pricing/calculator/>
- Azure コスト管理ドキュメント: <https://learn.microsoft.com/ja-jp/azure/cost-management-billing/>
- Azure Spot 仮想マシン: <https://learn.microsoft.com/ja-jp/azure/virtual-machines/spot-vms>
- Azure Advisor: <https://learn.microsoft.com/ja-jp/azure/advisor/>

---

## 次のドキュメント

- **[02-gpu-quota.md](02-gpu-quota.md)** — GPU SKU 選定と quota 申請
