# 05 — 後始末（重要・コスト対策）

**このステップを飛ばすと、月額数万〜数十万円が意図せず課金される可能性があります。** 必ず実施してください。

## 課金される主なリソース

| リソース | Compute 停止時 | Compute 起動時 |
|---|---|---|
| **Compute Instance (GPU VM)** | **停止** | 起動中のみ。A100 なら 約 **¥860/h**、T4 なら 約 **¥160/h** |
| **OS ディスク 120 GB (Premium SSD)** | **課金継続** | 課金継続 |
| **静的パブリック IP** | **課金継続**（約 ¥400/月） | 課金継続 |
| **Standard Load Balancer**（VNet 統合時） | **課金継続**（約 ¥3,000/月） | 課金継続 |
| Storage / Key Vault / App Insights / Container Registry | **課金継続**（合計 数百〜千円/月） | 課金継続 |

> [!IMPORTANT]
> **Compute Instance を停止しても、OS ディスク・静的 IP・依存リソースの課金は残ります。** 数週間〜1 か月使わない場合は Compute Instance の **削除**、プロジェクト完了時は **リソースグループごと削除** を選んでください。

## 選択肢

### A. 一時停止（当日中にまた使う）

Compute Instance の GPU/CPU 課金だけ止めます。数分で再起動できます。**ディスク・IP 課金は残ります。**

**Azure ML Studio で:**  
コンピューティング → `ci-tamgen-<yourname>-<suffix>` → **停止**

**CLI で:**

```bash
YOUR_NAME="taro"
RG="rg-spread1000-tamgen-drug-discovery-${YOUR_NAME}"
WS=$(az ml workspace list -g "${RG}" --query "[0].name" -o tsv)
CI=$(az ml compute list -g "${RG}" -w "${WS}" --query "[?type=='ComputeInstance'].name | [0]" -o tsv)

az ml compute stop \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}"
```

> [!TIP]
> `deploy.sh` および Bicep では **アイドル 60 分で自動停止** を設定済みですが、手動停止のほうが確実です。

### B. Compute Instance を削除（1 週間〜1 か月使わない）

Workspace と重み（Storage 内）は残し、GPU VM だけ削除します。次回は Compute Instance を作り直せば OK。

> [!WARNING]
> **Compute Instance を削除すると OS ディスクごと消えます。** `~/TamGen`（クローンしたリポジトリ）、`~/TamGen/checkpoints`（3.1 GB の重み）、conda 環境、`output/` の生成結果はすべて失われます。次回は `setup-tamgen.sh` を再実行し、再ダウンロード（合計 3.1 GB）と conda 環境構築（20〜30 分）が必要になります。
>
> **削除前に必ず保存**（Compute Instance 上の Jupyter ターミナルで実行）:
>
> ```bash
> # 生成結果とスクリプトを Workspace 共有ストレージ (Blob) に退避
> # ~/cloudfiles/ は全 Compute Instance から見える永続領域
> mkdir -p ~/cloudfiles/code/Users/$(whoami)/tamgen-archive
> cp -r ~/TamGen/output ~/cloudfiles/code/Users/$(whoami)/tamgen-archive/
> cp -r ~/TamGen/scripts ~/cloudfiles/code/Users/$(whoami)/tamgen-archive/ 2>/dev/null || true
> ```
>
> 重み（`checkpoints.zip` / `gpt_model.zip`）は Zenodo から再ダウンロード可能なため退避不要ですが、時間を短縮したい場合は `~/cloudfiles/` にコピーしておいてください。

```bash
az ml compute delete \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}" \
  --yes
```

これで OS ディスクと静的 IP の課金も止まります。**ただし Storage / KV / ACR / App Insights は残り、合計月数百〜千円程度の課金は続きます。**

### C. すべて削除（プロジェクト完了）

> [!WARNING]
> **この操作は取り消せません。** Workspace 内のデータ・生成分子はすべて消えます。事前に必要なファイルを手元にダウンロードしてください。

```bash
YOUR_NAME="taro"
RG="rg-spread1000-tamgen-drug-discovery-${YOUR_NAME}"

# 1. リソースグループ内の Key Vault 名を先に控える (削除後にパージするため)
KV_NAMES=$(az keyvault list -g "${RG}" --query "[].name" -o tsv)
LOCATION=$(az group show -n "${RG}" --query location -o tsv)

# 2. リソースグループごと削除 (完了まで 5-15 分)。--no-wait は付けない。
az group delete --name "${RG}" --yes

# 3. Key Vault はソフト削除保護 (7 日) が残る。放置しても課金は発生しないため通常はここで終了。
#    次回同名で作り直したい・7 日以内に確実にパージしたい場合のみ、以下を実行:
for kv in ${KV_NAMES}; do
  # 削除済み状態になっているか確認してからパージ
  if az keyvault show-deleted --name "${kv}" --location "${LOCATION}" -o none 2>/dev/null; then
    read -rp "Key Vault '${kv}' を完全パージしますか? (元に戻せません) [y/N]: " ANS
    if [[ "${ANS,,}" == "y" ]]; then
      az keyvault purge --name "${kv}" --location "${LOCATION}"
    fi
  fi
done
```

> [!WARNING]
> **`az keyvault list-deleted` を検索して自動パージしてはいけません。** 別プロジェクト・別ユーザーの Vault を巻き込んで削除する事故が発生します。必ずリソースグループから取得した名前のみをパージ対象にし、対話確認を挟んでください。

## 課金の確認

翌日以降、[Azure Portal → コスト管理 + 請求](https://portal.azure.com/#view/Microsoft_Azure_CostManagement/Menu/~/overview) の **コスト分析** で確認できます。フィルタで **タグ: scenario = tamgen-drug-discovery** を選ぶと、このクイックスタート分だけ切り出せます。

CLI で確認したい場合は Cost Management REST API を `az rest` で直接叩きます（`az costmanagement query` サブコマンドは現行の costmanagement 拡張から削除されています）。

> [!NOTE]
> 以下は `jq` と GNU `date` (`date -d`) を要求します。macOS では `brew install jq coreutils` で
> インストール後、`date` を `gdate` に読み替えてください。`jq` を入れずに実行したい場合は
> body を静的な JSON ファイルに保存して `--body @cost-query.json` で渡すこともできます。

```bash
SUB_ID=$(az account show --query id -o tsv)
# GNU date (-d) を使用。macOS の場合は 'gdate' に置換
if date -d "7 days ago" +%Y-%m-%d >/dev/null 2>&1; then
  START=$(date -d "7 days ago" +%Y-%m-%d)
elif command -v gdate >/dev/null 2>&1; then
  START=$(gdate -d "7 days ago" +%Y-%m-%d)
else
  # BSD date のフォールバック (macOS 標準)
  START=$(date -v-7d +%Y-%m-%d)
fi
END=$(date +%Y-%m-%d)

az rest --method post \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body "$(jq -n --arg s "${START}T00:00:00Z" --arg e "${END}T23:59:59Z" '{
    type: "Usage",
    timeframe: "Custom",
    timePeriod: {from: $s, to: $e},
    dataset: {
      granularity: "None",
      aggregation: {totalCost: {name: "Cost", function: "Sum"}},
      grouping: [{type: "Dimension", name: "ResourceId"}],
      filter: {tags: {name: "scenario", operator: "In", values: ["tamgen-drug-discovery"]}}
    }
  }')"
```

## 完了チェック

- [ ] Compute Instance が **停止** または **削除** 済み
- [ ] （プロジェクト完了時のみ）リソースグループごと削除済み
- [ ] 翌日以降、Cost Management で意図した金額に収まっていることを確認

これでクイックスタートは完了です 🎉  
問題が起きた場合は [troubleshooting.md](troubleshooting.md) を参照してください。

