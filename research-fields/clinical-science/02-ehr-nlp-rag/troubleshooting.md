# トラブルシューティング

このファイルは各 docs/ の各 § でカバーしきれない横断的な問題や、複雑な症状の切り分け手順を集めたものです。

## 1. デプロイ関連

### `SkuNotAvailable` (Azure OpenAI)

**症状**: Bicep デプロイで `SkuNotAvailable`

**原因**:
- 対象リージョンで `gpt-4o` や `text-embedding-3-large` のバージョンが提供されていない
- サブスクの Azure OpenAI アクセス承認がまだ

**確認**:
```bash
# 提供モデル一覧
az cognitiveservices model list --location $LOCATION \
  --query "[?kind=='OpenAI' && model.name=='gpt-4o'].{version:model.version, sku:model.skus[0].name}" \
  -o table

# アクセス承認済みか
az cognitiveservices account list-kinds --query "[?contains(@, 'OpenAI')]"
```

**対処**: リージョン変更（Sweden Central, East US 2 等） or Bicep パラメータの `deployGpt4o=false` にして一旦 skip し、Portal で提供バージョンを選択

### `InvalidTemplateDeployment`: OpenAI subdomain conflict

**症状**: `The specified customSubDomainName is already in use`

**原因**: 同じ subdomain 名のリソースがサブスク内で soft-delete 中

**対処**: `UNIQUE_SUFFIX` を変える or `05-cleanup.md` の purge 手順を実行

### 権限エラー

**症状**: `AuthorizationFailed: does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write'`

**原因**: 呼び出し元に `User Access Administrator` (RBAC 割当権限) が無い

**対処**:
- 機関の Azure 管理者に依頼して `User Access Administrator` を付与してもらう
- または管理者に `infra/deploy.sh` の RBAC 部分を代行してもらう

## 2. 認証・トークン関連

### `DefaultAzureCredential` が失敗

**症状**: Python から `DefaultAzureCredential failed to retrieve a token`

**確認順**:
1. `az account show` でログイン確認
2. `az account get-access-token --resource https://cognitiveservices.azure.com` でトークン取得可否
3. `az account get-access-token --resource https://search.azure.com` （AI Search）
4. `az account get-access-token --resource https://storage.azure.com` （Storage）

**対処**:
- ログイン切れ → `az login`
- テナント違い → `az login --tenant <TENANT_ID>`
- Managed Identity 環境（AML compute 等）で意図しない ID が拾われている → 環境変数 `AZURE_CLIENT_ID` を明示

### 権限伝播ラグ

新規 RBAC 割当は反映まで **最大 5-10 分**かかることがあります。`Forbidden` が続く場合はまず時間を空けて再試行してください。

## 3. AI Search 関連

### `content_vector` フィールドの次元不一致

**症状**: `The vector field 'content_vector' has dimensionality 1536, expected 3072`

**原因**: 過去に `text-embedding-3-small` (1536dim) や `text-embedding-ada-002` (1536dim) で作ったインデックスが残っている

**対処**:
```bash
# インデックス削除
python3 -c "
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
c = SearchIndexClient(endpoint=os.environ['SEARCH_ENDPOINT'], credential=DefaultAzureCredential())
c.delete_index(os.environ.get('SEARCH_INDEX','ehr-notes'))
print('deleted')
"

# 再作成
python scripts/index_docs.py
```

### Semantic ranker が使えない

**症状**: `Semantic configuration ... not found` または `Feature not supported at this tier`

**原因**: Basic SKU の semantic ranker (free tier) は **リージョンによって未提供**

**対処**: `scripts/query_rag.py` の `query_type` と `semantic_configuration_name` を削除して純ハイブリッドに切り替え。または Standard SKU 以上に上げる（コスト増）

## 4. Azure OpenAI 関連

### `429 Too Many Requests`

**症状**: 埋め込みや chat で 429

**原因**: 1 分あたりの TPM (tokens per minute) を超過

**対処**:
- 一時的なら数分待って再実行
- 恒常的なら Azure Portal → OpenAI リソース → **Quotas** から TPM 増加申請（本 quickstart 前提の合成データ 3 件なら発生しないはず）
- または Bicep パラメータ `gpt4oTpmCapacityK` / `embeddingTpmCapacityK` を上げて再デプロイ

### `content_filter` エラー

**症状**: `The response was filtered due to the prompt triggering Azure OpenAI's content management policy`

**原因**: プロンプトまたはコンテキストに Azure Content Safety がヒット（暴力・自傷等の医療テキストは誤検知しやすい）

**対処**:
- コンテキストを短くする
- Bicep の `raiPolicyName` を独自ポリシーに切り替え（Portal で「Content Filters」から設定）
- 完全 opt-out は不可（Microsoft 側で必須）

## 5. コスト関連

### 「動作確認終わったのに課金が続いている」

**原因**: AI Search が起動したままの可能性が高い

**確認**:
```bash
az resource list -g "$RG" -o table
# AI Search リソースがまだあれば → 起動＝課金
```

**対処**: [`05-cleanup.md`](docs/05-cleanup.md) を実行して RG ごと削除

### Cost Analysis に反映されない

**原因**: Cost データは **8〜24 時間遅延**

**対処**: 翌日再確認。日本時間の朝 9 時ごろに前日分がまとまることが多い

## 6. データ関連

### 実患者データを誤ってアップロードした

**⚠️ この quickstart のテンプレートは合成データ専用構成であり、実患者データを扱う場面ではそもそもデプロイしないでください。** 万が一の誤アップロード時は**「①即時封じ込め (Initial Containment) → ②削除処置 (Destruction) → ③完全遮断 (Full Isolation) → ④通報・記録 (Reporting)」の順**でダメージコントロールします。**削除処置を「削除経路そのものを閉じる前」に完了させる**のがポイントです（先に public network を切ってしまうと削除操作もエラーになるため）。

#### ⓪ 初動: 機関 CIO/IRB への即時通報 + ローカル PHI の証拠保全隔離

**⚠️ 削除アクション (②) の前に、必ず機関の CIO/情報セキュリティ担当・IRB 事務局に第一報を入れ、対応方針の合意（証拠保全・削除範囲・報告義務）を得てから進めてください。** インシデント処理は「①〜③ を単独判断で実行する前に、④の通報経路を先に開いておく」設計です。

- 通報チャネル（例: 機関の情報セキュリティインシデント窓口 / IRB 事務局 / 個人情報保護管理者）を開く
- 対応者・実施時刻・スコープ (RG/リソース ID/blob 名) を記録開始
- 以下の隔離コマンドは**証拠保全のため元ファイルを削除せず "quarantine ディレクトリへ移動"** します（Git 履歴・OneDrive/クラウド同期・バックアップ側の purge は機関チーム主導で実施）

#### ① 即時封じ込め (Initial Containment): 認証情報を無効化 + local auth を停止

削除操作を実行する**指名対応者 (responder)** の AAD トークン経由アクセスは残しつつ、それ以外の全ての経路（Shared Key・API キー・SAS・他ユーザーの RBAC・Search MSI）を無効化します。**キー系は全て「表示せず更新」（`-o none`）**でローテートし、新しいキーが shell 履歴に残らないようにします。

- **Storage Shared Key 認証を無効化**: `az storage account update --allow-shared-key-access false` — キーによる直接アクセスを即時遮断（AAD 経路は影響なし）
- **Storage の Shared Key をローテート（`-o none`）**: 万一の漏洩に備え primary/secondary を新値に。アカウントキー署名 SAS を無効化
- **User-delegation SAS を全て取り消す**: `az storage account revoke-delegation-keys` — AAD 由来の user-delegation SAS はキーローテートでは無効化されない
- **AI Search local auth（API キー）を無効化**: `az resource update ... --set properties.authOptions=null properties.disableLocalAuth=true`（`authOptions.aadOrApiKey` を有効にしたまま `disableLocalAuth=true` にはできないため、`authOptions` を先に `null` にする）
- **AI Search 管理キーをローテート（`-o none`）**: primary/secondary を新値に
- **Azure OpenAI local auth（API キー）を無効化**: `az resource update ... --set properties.disableLocalAuth=true`（**`apiProperties.disableLocalAuth` ではなく top-level の `properties.disableLocalAuth`**。Bicep でも同様）
- **Azure OpenAI キーをローテート（`-o none`）**: `az cognitiveservices account keys regenerate` を key1/key2 双方に実施
- **指名対応者以外の RBAC を全て剥奪**: **必ず `--include-inherited` を付けて RG・サブスクリプションスコープからの継承割当ても列挙**（`--include-inherited` を付けないと `Storage Blob Data Contributor` を持つ RG/Subscription オーナーが見えず、封じ込め後もアクセスされ得る）。列挙結果を確認し、削除するのは**リソーススコープの割当てのみ**（RG/Subscription スコープを勝手に消すと機関全体の運用が壊れる）。継承側は機関管理者に別途連絡して剥奪を依頼。**AI Search MSI に付与された `Cognitive Services OpenAI User` と `Storage Blob Data Reader` も剥奪**（実データにアクセスできる経路を全て塞ぐ）

#### ② 削除処置 (Destruction): AAD 認証で削除

> **⚠️ 注意**: RBAC 剥奪 / user-delegation-key 取り消しは **最大数分の伝播遅延**があり、Shared Key 無効化直後もキャッシュされたトークンで数分間アクセスが継続する可能性があります。**より強い封じ込めが必要な場合は、Phase ② の削除操作を private endpoint 経由で実施可能な環境を用意した上で `--public-network-access Disabled`** に切り替える構成も選択肢です（public network を切ると同時に対応者 IP 経由の削除もブロックされるため、firewall rule での "public 有効 + 対応者 IP のみ許可" とは併用できません）。本手順書は private endpoint 未整備の novice 環境を想定し、最も汎用的な「削除→ネットワーク遮断」の順を採用しています。

- **アクティブな blob を削除**（`az storage blob delete --auth-mode login` — AAD 認証を明示）
- **AI Search インデックスを再構築**（丸ごと削除 → 空の状態を確認）

soft-delete で 7 日間 `undelete` 可能な状態が残ります（**Azure の設計上、保持期間を短縮する API は提供されていない**。Microsoft サポート依頼でも短縮不可 — 保持期間は削除保護 SLA の一部）。取りうる選択肢:
- **A. 保持期間の満了 (7 日) を待つ**（推奨・監査ログで経過を記録）
- **B. コンテナー削除** — コンテナー自体は container soft-delete 対象になり同じく 7 日保持
- **C. ストレージアカウント削除** — アカウント削除は **container soft-delete とは別の "deleted account recovery"** で、**Microsoft の best-effort により最大 14 日間復元可能**（保証期間ではないが、期間中は完全消去が保証されない）

**Azure OpenAI abuse monitoring ログ**: [modified-abuse-monitoring](https://learn.microsoft.com/ja-jp/azure/ai-foundry/openai/concepts/abuse-monitoring) が承認済みならログ保存自体が抑止されている可能性あり。**ログの即時削除はできず、保持期間の満了を待つ**運用となります。

#### ③ 完全遮断 (Full Isolation): 削除完了後にネットワークを塞ぐ

Phase ① で local auth (Shared Key / API キー) と responder 以外の RBAC は既に閉じてあります。削除処置が完了した後、public network を遮断して残りの侵入経路を塞ぎます:

- **Storage の公開ネットワークを遮断**: `az storage account update --public-network-access Disabled`
- **AI Search の公開ネットワークを遮断**: `az search service update --public-network-access disabled`
- **Azure OpenAI の公開ネットワークを遮断**: `az cognitiveservices account update --custom-domain <name>` + Bicep `publicNetworkAccess: 'Disabled'`（または `az resource update` で直接更新）
- **指名対応者の RBAC も剥奪**: Storage / Search / OpenAI 全て `az role assignment delete`（削除処置完了後の最終ステップ）
- （必要なら）**リソースグループごと削除**（本 quickstart の合成データ用途なら最も確実）

#### ④ 通報・記録 (Reporting)

- **機関の CIO / 情報セキュリティ担当・IRB 事務局にただちに報告**
- Microsoft サポートへの起票は初動として可能だが、**保持期間中の即時完全消去の保証は得られない**
- Log Analytics に送信された削除操作・アクセスログを保存し、インシデント記録に添付
- **インシデント記録には「アクセス封じ込め時刻」と「保持期間満了予定時刻」を必ず区別して記載**

```bash
set -Eeuo pipefail  # 途中の失敗を絶対に無視しない（PHI インシデント処理は一部成功で止めない）

# ⓪ ローカル PHI の証拠保全隔離（再アップロード防止）
# 実行中の PC・OneDrive・Git 作業ツリーに残っている PHI を quarantine ディレクトリへ移動し、
# 再度 `bash scripts/upload_docs.py` 実行時に混入しないようにする。
# 相対パス構造を保持したまま移動（同名 basename の上書きを防ぎ、証拠の chain-of-custody を維持）
QUARANTINE_DIR="$HOME/phi-quarantine-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$QUARANTINE_DIR"
chmod 700 "$QUARANTINE_DIR"
# 例: INCIDENT_LOCAL_FILES=(inputs/sample-notes/patient1.md inputs/sample-notes/patient2.md)
: "${INCIDENT_LOCAL_FILES[@]:?INCIDENT_LOCAL_FILES 配列にローカルの PHI ファイルパスを入れてください}"
for F in "${INCIDENT_LOCAL_FILES[@]}"; do
  if [[ -e "$F" ]]; then
    DEST="$QUARANTINE_DIR/$F"
    mkdir -p "$(dirname "$DEST")"
    if [[ -e "$DEST" ]]; then
      echo "🛑 quarantine 先に既存ファイル: $DEST (上書きせず中断)" >&2
      exit 1
    fi
    mv -v --no-clobber "$F" "$DEST"
    # ハッシュ記録（証拠保全）
    sha256sum "$DEST" >> "$QUARANTINE_DIR/SHA256SUMS.txt"
  fi
done
echo "[note] Git 履歴・OneDrive/クラウド同期・バックアップにも同一 PHI が残っている可能性があります。"
echo "       機関のインシデント対応チームと連携し、Git 履歴書き換え（git filter-repo 等）・"
echo "       同期先の削除・バックアップからの purge を必ず実施してください。"

# ① 即時封じ込め: 認証情報の無効化 + local auth 停止（AAD 経路は維持）
# Shared Key を即時無効化（AAD 削除は影響なし）
az storage account update -n "$STORAGE_ACCOUNT" -g "$RG" --allow-shared-key-access false -o none
# 万一の漏洩対策: 全キーをローテート（`-o none` で新キーを表示しない）
az storage account keys renew -n "$STORAGE_ACCOUNT" -g "$RG" --key primary -o none
az storage account keys renew -n "$STORAGE_ACCOUNT" -g "$RG" --key secondary -o none
# AAD 由来の user-delegation SAS も取り消し
az storage account revoke-delegation-keys -n "$STORAGE_ACCOUNT" -g "$RG"

# AI Search: authOptions を null にした上で local auth 無効化 + キーローテート
az resource update -g "$RG" -n "$SEARCH_NAME" \
  --resource-type "Microsoft.Search/searchServices" \
  --set properties.authOptions=null properties.disableLocalAuth=true -o none
az search admin-key renew -g "$RG" --service-name "$SEARCH_NAME" --key-kind primary -o none
az search admin-key renew -g "$RG" --service-name "$SEARCH_NAME" --key-kind secondary -o none

# Azure OpenAI: local auth 無効化（top-level properties.disableLocalAuth）+ キーローテート
az resource update -g "$RG" -n "$OPENAI_NAME" \
  --resource-type "Microsoft.CognitiveServices/accounts" \
  --set properties.disableLocalAuth=true -o none
az cognitiveservices account keys regenerate -g "$RG" -n "$OPENAI_NAME" --key-name key1 -o none
az cognitiveservices account keys regenerate -g "$RG" -n "$OPENAI_NAME" --key-name key2 -o none

# 監査 + RBAC 剥奪（順序: 直接割当てを先に消してから、継承割当てを機関管理者に依頼）
RESPONDER_OID=$(az ad signed-in-user show --query id -o tsv)
SUB_ID=$(az account show --query id -o tsv)
STG_SCOPE="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
SRCH_SCOPE="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.Search/searchServices/$SEARCH_NAME"
OAI_SCOPE="/subscriptions/$SUB_ID/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$OPENAI_NAME"

# ①-a 直接割当ての即時削除（責任範囲内）
# 対応者が「グループ経由」でしかロールを持たない場合、そのグループの直接割当てを消すと
# ロックアウトされる。以下は「グループを保護対象に含めるとメンバー全員が残る」トレードオフの解消策:
# (1) 対応者本人に一時的な直接ロール（削除・index 操作に必要な完全な権限セット）を機関管理者 or UAA 権限保持者から付与し、
# (2) 伝播 (~1-3 分) を待ってから canary write/delete で削除権限を実際に検証してから、
# (3) `PROTECTED_OIDS=$RESPONDER_OID` のまま（グループ OID は含めない）で本ブロックを実行する。
# こうすることで「グループの直接割当てが消えても対応者本人の直接割当てで削除継続可能」となる。
#
# 一時的な直接ロール付与手順:
#   for ROLE_SCOPE in \
#     "Storage Blob Data Contributor|$STG_SCOPE" \
#     "Search Service Contributor|$SRCH_SCOPE"        `# index の delete/create に必須` \
#     "Search Index Data Contributor|$SRCH_SCOPE"     `# doc レベル操作` \
#     "Cognitive Services OpenAI Contributor|$OAI_SCOPE"; do
#     ROLE="${ROLE_SCOPE%%|*}"; SCOPE="${ROLE_SCOPE##*|}"
#     az role assignment create --assignee "$RESPONDER_OID" --role "$ROLE" --scope "$SCOPE" -o none
#   done
#   sleep 120  # RBAC 伝播待ち
: "${PROTECTED_OIDS:=$RESPONDER_OID}"  # デフォルトは責任者本人のみ
PROTECT_JMESPATH=$(printf ",'%s'" $PROTECTED_OIDS); PROTECT_JMESPATH="[${PROTECT_JMESPATH:1}]"

# 事前検証 (canary): 対応者が「実際に write/delete できる」ことを一時 blob で確認する
# read/list だけの権限では Phase ② の削除が失敗するため、write/delete まで検証する
# NOTE: CANARY_TMP は post-check (①-a-post) でも再利用するため、スクリプト終了時まで保持
#       (trap でクリーンアップ)。以前は上書き前に rm していて post-check が --file 参照エラーになるバグがあった。
CANARY_NAME=".phi-incident-canary-$(date -u +%Y%m%dT%H%M%SZ).txt"
CANARY_TMP=$(mktemp)
trap 'rm -f "$CANARY_TMP"' EXIT
echo "canary" > "$CANARY_TMP"
if ! az storage blob upload --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
     --name "$CANARY_NAME" --file "$CANARY_TMP" --auth-mode login --overwrite -o none 2>/dev/null; then
  echo "🛑 STOP: 対応者は Blob write 権限がありません（Storage Blob Data Contributor 相当が必要）。" >&2
  echo "  上記コメントの一時ロール付与手順を実行し、~2 分待ってから再実行してください（exit 6）。" >&2
  exit 6
fi
if ! az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
     --name "$CANARY_NAME" --auth-mode login -o none 2>/dev/null; then
  echo "🛑 STOP: 対応者は Blob delete 権限がありません。exit 6" >&2
  exit 6
fi
# 注意: CANARY_TMP は消さない (post-check で再利用)。trap EXIT で最後に削除される。

# AI Search canary: index 作成/削除 (Service Contributor 相当) が実行可能か検証
if ! python3 - <<'PY' 2>/dev/null; then
import os, sys, uuid
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SimpleField, SearchFieldDataType
c = SearchIndexClient(endpoint=os.environ["SEARCH_ENDPOINT"], credential=DefaultAzureCredential())
name = f"canary-{uuid.uuid4().hex[:8]}"
idx = SearchIndex(name=name, fields=[SimpleField(name="id", type=SearchFieldDataType.String, key=True)])
c.create_index(idx); c.delete_index(name)
PY
  echo "🛑 STOP: 対応者は AI Search index の create/delete 権限がありません（Search Service Contributor が必要）。exit 6" >&2
  exit 6
fi

# 管理面 canary: RBAC 削除権限 (User Access Administrator or Owner) と Storage/OpenAI network 更新権限を検証
# これらはグループ経由の場合、①-a のグループ削除で失われる可能性があるため事前検証する
# (a) role assignment 一覧取得（read 権限確認）
if ! az role assignment list --scope "$STG_SCOPE" --query "[0].id" -o tsv > /dev/null 2>&1; then
  echo "🛑 STOP: 対応者は RBAC 一覧取得権限がありません（Reader 相当が必要）。exit 6" >&2
  exit 6
fi
# (b) canary role assignment を作成→削除して "write" 権限を検証（対応者本人に Reader を一時付与→削除）
CANARY_RA=$(az role assignment create --assignee "$RESPONDER_OID" --role "Reader" --scope "$STG_SCOPE" --query id -o tsv 2>/dev/null || true)
if [[ -z "$CANARY_RA" ]]; then
  echo "🛑 STOP: 対応者は RBAC 作成権限がありません。①-a でグループ削除するとロックアウトされます（User Access Administrator or Owner の直接付与が必要）。exit 6" >&2
  exit 6
fi
if ! az role assignment delete --ids "$CANARY_RA" -o none 2>/dev/null; then
  echo "🛑 STOP: 対応者は RBAC 削除権限がありません。exit 6" >&2
  exit 6
fi
# (c) Storage / OpenAI management-plane 更新権限の what-if
if ! az storage account show -n "$STORAGE_ACCOUNT" -g "$RG" --query publicNetworkAccess -o tsv > /dev/null 2>&1; then
  echo "🛑 STOP: 対応者は Storage account 管理面 read 権限がありません。exit 6" >&2
  exit 6
fi
if ! az cognitiveservices account show -n "$OPENAI_NAME" -g "$RG" --query "properties.publicNetworkAccess" -o tsv > /dev/null 2>&1; then
  echo "🛑 STOP: 対応者は Cognitive Services 管理面 read 権限がありません。exit 6" >&2
  exit 6
fi
echo "  [ok] canary 検証完了: データ面 write/delete + 管理面 RBAC/network 変更権限を対応者本人が直接保有"

for SCOPE in "$STG_SCOPE" "$SRCH_SCOPE" "$OAI_SCOPE"; do
  az role assignment list --scope "$SCOPE" \
    --query "[?!contains(${PROTECT_JMESPATH}, principalId) && scope=='$SCOPE'].id" -o tsv \
    | xargs -r -I{} az role assignment delete --ids "{}"
done

# ①-a-post: グループ割当て削除後に「対応者本人の直接権限だけで」Phase ② が実行可能かを再検証
# 事前 canary はグループ経由でも通過してしまうため、削除後に必ず再実行する
echo "=== ①-a 削除後の権限再検証 ==="
sleep 30  # RBAC 削除の伝播待ち
# データ面 write/delete 再検証
CANARY2_NAME=".phi-incident-canary2-$(date -u +%Y%m%dT%H%M%SZ).txt"
if ! az storage blob upload --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
     --name "$CANARY2_NAME" --file "$CANARY_TMP" --auth-mode login --overwrite -o none 2>/dev/null; then
  echo "🛑 STOP: グループ割当て削除後、対応者は Blob write 権限を失いました。" >&2
  echo "  機関管理者から直接ロール (Storage Blob Data Contributor 等) を再付与し、再実行してください（exit 7）。" >&2
  exit 7
fi >/dev/null 2>&1 || true
az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
  --name "$CANARY2_NAME" --auth-mode login -o none 2>/dev/null || true
# 管理面 RBAC write 再検証
CANARY_RA2=$(az role assignment create --assignee "$RESPONDER_OID" --role "Reader" --scope "$STG_SCOPE" --query id -o tsv 2>/dev/null || true)
if [[ -z "$CANARY_RA2" ]]; then
  echo "🛑 STOP: グループ削除後、対応者は RBAC 変更権限を失いました（Phase ③ で剥奪不能）。" >&2
  echo "  機関管理者から User Access Administrator を直接付与してから再実行（exit 7）。" >&2
  exit 7
fi
az role assignment delete --ids "$CANARY_RA2" -o none 2>/dev/null || true
echo "  [ok] グループ削除後も対応者本人の直接権限で Phase ②/③ 実行可能"

# ①-b 継承割当てを再監査（--include-inherited は責任外の親スコープを含む）
# 「PHI に実質アクセスできる/RBAC を再付与できる」ロールのみを fail-closed の対象とし、
# Reader / Monitoring 系の閲覧のみロールは監査ログ表示に留める（緊急削除を無闇にブロックしない）
DANGEROUS_ROLES=(
  "Owner" "Contributor" "User Access Administrator" "Role Based Access Control Administrator"
  "Storage Blob Data Owner" "Storage Blob Data Contributor" "Storage Blob Data Reader"
  "Storage Account Contributor" "Storage Account Key Operator Service Role"
  "Search Service Contributor" "Search Index Data Contributor" "Search Index Data Reader"
  "Cognitive Services Contributor" "Cognitive Services OpenAI Contributor" "Cognitive Services OpenAI User" "Cognitive Services User"
)
DANGEROUS_JMESPATH=$(printf ",'%s'" "${DANGEROUS_ROLES[@]}"); DANGEROUS_JMESPATH="[${DANGEROUS_JMESPATH:1}]"

echo "=== 【監査 1a】非対応者への継承割当ての一覧（全件、参考表示） ==="
for SCOPE in "$STG_SCOPE" "$SRCH_SCOPE" "$OAI_SCOPE"; do
  echo "--- Scope: $SCOPE ---"
  az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?!contains(${PROTECT_JMESPATH}, principalId) && scope!='$SCOPE'].{principal:principalName, role:roleDefinitionName, scope:scope}" -o table
done

echo "=== 【監査 1b】非対応者への継承割当てのうち、データ/RBAC 変更可能な危険ロール（fail-closed 対象） ==="
INHERITED_FOUND=0
# 「未知の継承ロールは全て停止条件」= 既知の SAFE_ROLES 以外は全て危険扱い（fail-secure）
# SAFE_ROLES は「PHI にも RBAC 再付与にもアクセスできないことが確定している組み込みロール」のみ
# 注意: "Log Analytics Reader" / "Monitoring Reader" は本テンプレートでは SAFE 扱いしない。
#       Search の QueryLogs (Query.Search) を診断で有効化すると生の臨床質問が
#       AzureDiagnostics.Query_s に格納されうるため、Log Analytics 上の閲覧権限は
#       PHI 閲覧権限として扱う必要がある (本テンプレートでは既定 QueryLogs 無効化済みだが、
#       将来的に有効化する運用者に対して fail-secure を維持する)。
SAFE_ROLES=(
  "Reader" "Security Reader"
  "Cost Management Reader" "Cost Management Contributor"
  "Tag Contributor"
)
SAFE_JMESPATH=$(printf ",'%s'" "${SAFE_ROLES[@]}"); SAFE_JMESPATH="[${SAFE_JMESPATH:1}]"

for SCOPE in "$STG_SCOPE" "$SRCH_SCOPE" "$OAI_SCOPE"; do
  echo "--- Scope: $SCOPE ---"
  # 危険 = 未知（SAFE_ROLES に含まれない）or 明示的な既知データ/RBAC 系ロール
  az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?!contains(${PROTECT_JMESPATH}, principalId) && scope!='$SCOPE' && (!contains(${SAFE_JMESPATH}, roleDefinitionName) || contains(${DANGEROUS_JMESPATH}, roleDefinitionName))].{principal:principalName, role:roleDefinitionName, scope:scope}" -o table
  COUNT=$(az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?!contains(${PROTECT_JMESPATH}, principalId) && scope!='$SCOPE' && (!contains(${SAFE_JMESPATH}, roleDefinitionName) || contains(${DANGEROUS_JMESPATH}, roleDefinitionName))] | length(@)" -o tsv)
  [[ "$COUNT" -gt 0 ]] && INHERITED_FOUND=1
done
# ⚠️ カスタムロールは名前だけでは権限判定できないため、上記フィルタで全て「未知＝危険」として扱う。
# 誤検知を減らしたい場合のみ、機関固有の安全カスタムロールを SAFE_ROLES に追記すること。

echo "=== 【監査 2】対応者自身の継承ロール（Owner/Contributor 等の広範な親スコープ権限） ==="
echo "  ※ 対応者は Phase ② の削除操作を実行するため、この継承権限は Phase ② 完了まで残す設計。"
echo "     Phase ③ 完了後に機関管理者が剥奪します（③-b で再確認）。"
for SCOPE in "$STG_SCOPE" "$SRCH_SCOPE" "$OAI_SCOPE"; do
  az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?contains(${PROTECT_JMESPATH}, principalId) && scope!='$SCOPE'].{role:roleDefinitionName, scope:scope}" -o table
done

# ⚠️ fail-closed: 非対応者への危険ロール継承が 1 件でもあれば Phase ② に進む前に機関管理者へ剥奪依頼
if [[ "$INHERITED_FOUND" -eq 1 ]]; then
  echo "" >&2
  echo "🛑 STOP: 非対応者への「データアクセス/RBAC 変更が可能な」継承ロールが検出されました。" >&2
  echo "  以下を機関管理者に依頼してから Phase ② に進んでください:" >&2
  echo "  - RG/Subscription スコープの Storage/Search/OpenAI に関する当該ロール剥奪" >&2
  echo "  - 剥奪が現実的でない場合、private endpoint への即時切替により対応者以外のネットワーク経路を先に遮断" >&2
  exit 2
fi

# ② 削除処置: AAD 認証でインシデント該当データを削除
# ⚠️ 単一 blob の削除だけで済ませない。実患者データが混入した blob のリストを INCIDENT_BLOBS に入れ、全て削除する。
# INCIDENT_BLOBS=(patient1.md patient2.md ...) のように事前に決めておくこと
: "${INCIDENT_BLOBS[@]:?INCIDENT_BLOBS 配列に削除対象 blob 名を入れてください（bash 配列）}"
for BLOB in "${INCIDENT_BLOBS[@]}"; do
  az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
    --name "$BLOB" --auth-mode login --delete-snapshots include
done

# AI Search インデックスを丸ごと削除（部分削除ではなく確実に）
python3 - <<'PY'
import os
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
idx = os.environ.get("SEARCH_INDEX", "ehr-notes")
c = SearchIndexClient(endpoint=os.environ["SEARCH_ENDPOINT"], credential=DefaultAzureCredential())
c.delete_index(idx)
print(f"deleted index: {idx}")
PY

# ②-a 完全性チェック: 対象 blob が active に残っていないことを検証（1件ずつ exists で確認）
echo "=== 削除完全性チェック ==="
REMAINING_BLOBS=()
for BLOB in "${INCIDENT_BLOBS[@]}"; do
  EXISTS=$(az storage blob exists --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
    --name "$BLOB" --auth-mode login --query exists -o tsv)
  if [[ "$EXISTS" == "true" ]]; then
    REMAINING_BLOBS+=("$BLOB")
  fi
done
if [[ "${#REMAINING_BLOBS[@]}" -gt 0 ]]; then
  echo "🛑 STOP: 以下の PHI blob が active のまま残っています。Phase ③ に進まないでください:" >&2
  printf '  - %s\n' "${REMAINING_BLOBS[@]}" >&2
  exit 3
fi
echo "  [ok] 対象 blob (${#INCIDENT_BLOBS[@]} 件) は全て active から消滅"

# soft-delete 側の状態を記録（削除された時刻を監査ログに残す）
az storage blob list --account-name "$STORAGE_ACCOUNT" --container-name "$DOCS_CONTAINER" \
  --include d --auth-mode login --query "[?deleted].{name:name, deletedTime:properties.deletedTime}" -o table

# ③ 完全遮断: public network を塞ぎ、対応者の RBAC も剥奪
az storage account update -n "$STORAGE_ACCOUNT" -g "$RG" --public-network-access Disabled -o none
az search service update -g "$RG" --name "$SEARCH_NAME" --public-network-access disabled -o none
az resource update -g "$RG" -n "$OPENAI_NAME" \
  --resource-type "Microsoft.CognitiveServices/accounts" \
  --set properties.publicNetworkAccess=Disabled -o none

# ③-a 対応者ロールの剥奪（各リソーススコープ直接割当てのみ。継承分は機関管理者依頼）
# 注: Phase ①-a の一時ロール付与手順で "Cognitive Services OpenAI Contributor" を付けた場合は
#     それも必ず含める。一致しない場合は "no matching" として tolerated される。
for SPEC in \
  "Storage Blob Data Contributor|$STG_SCOPE" \
  "Search Index Data Contributor|$SRCH_SCOPE" \
  "Search Service Contributor|$SRCH_SCOPE" \
  "Cognitive Services OpenAI User|$OAI_SCOPE" \
  "Cognitive Services OpenAI Contributor|$OAI_SCOPE"; do
  ROLE="${SPEC%%|*}"; SCOPE="${SPEC##*|}"
  # 既に存在しない場合のみ許容し、それ以外の失敗（権限不足など）は上位に伝搬させる
  OUT=$(az role assignment delete --assignee "$RESPONDER_OID" --role "$ROLE" --scope "$SCOPE" 2>&1) || {
    if ! echo "$OUT" | grep -qi "no matching\|not found\|does not exist"; then
      echo "🛑 responder RBAC 剥奪失敗: role=$ROLE scope=$SCOPE" >&2
      echo "$OUT" >&2
      exit 4
    fi
  }
done

# ③-b 対応者の effective access が空になったことを検証（残っていれば非ゼロ終了）
echo "=== 対応者の effective access 確認（PHI 領域） ==="
REMAINING_ACCESS=0
for SCOPE in "$STG_SCOPE" "$SRCH_SCOPE" "$OAI_SCOPE"; do
  echo "--- Scope: $SCOPE ---"
  az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?contains(${PROTECT_JMESPATH}, principalId)].{role:roleDefinitionName, scope:scope}" -o table
  COUNT=$(az role assignment list --scope "$SCOPE" --include-inherited \
    --query "[?contains(${PROTECT_JMESPATH}, principalId)] | length(@)" -o tsv)
  [[ "$COUNT" -gt 0 ]] && REMAINING_ACCESS=$((REMAINING_ACCESS + COUNT))
done
if [[ "$REMAINING_ACCESS" -gt 0 ]]; then
  echo "" >&2
  echo "⚠️ 対応者（本人 or 所属グループ）の親スコープ Owner/Contributor 等が $REMAINING_ACCESS 件残存しています。" >&2
  echo "   機関管理者に剥奪依頼し、完了確認まで本インシデントを close しないでください（exit 5）。" >&2
  exit 5
fi
echo "  [ok] 対応者の effective access は空"

# ④ 通報・記録
# - 機関の CIO/情シス/IRB へ即時報告
# - Microsoft サポート起票（保持期間短縮の保証はないと理解した上で相談）
# - Log Analytics のアクセスログ・削除操作ログをインシデント記録に添付
```

> [!IMPORTANT]
> **「削除した」と「完全消去された」は別物**です。blob/container soft-delete は 7 日、**storage account の "deleted account recovery" は Microsoft の best-effort により最大 14 日**（保証ではないが復元可能な可能性あり）で保持されます。Microsoft サポートも保持期間中の即時完全消去は提供していません（保持期間は削除保護 SLA の一部）。<br>
> また、**先に `public-network-access=Disabled` や RBAC 剥奪を実施してしまうと、その後の削除操作 (`az storage blob delete`) も失敗**します。必ず「削除処置 → 完全遮断」の順で実行してください（本手順書はその順序で構成されています）。

## 参照

- [`../../docs/00-azure-account-setup.md`](../../../docs/00-azure-account-setup.md)
- [`../../docs/01-cost-management.md`](../../../docs/01-cost-management.md)
- [`../../docs/02-gpu-quota.md`](../../../docs/02-gpu-quota.md)
