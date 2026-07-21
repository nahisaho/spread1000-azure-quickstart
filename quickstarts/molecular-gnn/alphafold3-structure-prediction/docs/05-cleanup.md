# 05 — クリーンアップ（課金停止）と DB の永続化

所要 10 分。目的別に手順を選んでください。

## 課金される主なリソース

| リソース | 課金モデル | 停止方法 |
|---|---|---|
| **Compute Instance (H100)** | **停止** | 起動中のみ、約 **¥1,637/h** |
| **Compute Instance (A100)** | **停止** | 起動中のみ、約 **¥861/h** |
| Compute Instance の OS ディスク | **削除** | 停止中でも Premium SSD 120GB ≒ ¥2,500/月 |
| **`/mnt` 一時 NVMe** | 自動 | **停止と同時に全消去。永続化不可** |
| 静的パブリック IP | **削除** | 停止中でも ≒ ¥400/月 |
| Storage / Key Vault / App Insights / ACR | **削除** | 合計 月数百〜千円 |
| （DB 永続化する場合）Azure Files NFS | 従量 | 630GB Premium NFS ≒ 月 ¥13,000〜¥20,000 |
| Workspace 本体 | 無料 | 削除しても課金には影響しない |

> [!IMPORTANT]
> **Compute Instance を停止しても、OS ディスク・静的 IP・依存リソースの課金は残ります。** 数週間〜1 か月使わない場合は Compute Instance の **削除**、プロジェクト完了時は **リソースグループごと削除** を選んでください。

> [!WARNING]
> **`/mnt` は「停止」だけで消去されます**（一時ストレージのため）。
> `/mnt/af3/outputs` にある推論結果は **停止/削除前に必ず退避** してください。

---

## ⚠ Compute Instance を停止する前にやること

Compute Instance 上の Jupyter ターミナルで以下を実行し、
**推論結果と MSA データを永続領域 (`~/cloudfiles`) に退避**してください:

```bash
# 出力を永続領域（Workspace 共有 Blob）にコピー
mkdir -p ~/cloudfiles/code/Users/$(whoami)/af3-archive
cp -r /mnt/af3/outputs ~/cloudfiles/code/Users/$(whoami)/af3-archive/

# TERMS_OF_USE.md を含めてコピーされているか確認
find ~/cloudfiles/code/Users/$(whoami)/af3-archive -name TERMS_OF_USE.md
```

> [!IMPORTANT]
> **`af3.bin` はマウントされた `~/cloudfiles` に置かないでください。**
> `~/cloudfiles` は Workspace 上の全 Compute Instance 利用者から見える可能性があり、
> AF3 Terms of Use の再配布禁止条項に抵触する恐れがあります。
> 個人承認の場合は `af3.bin` を Compute Instance ごと削除するか、
> 削除前にローカル PC にダウンロードして保管してください。

---

## 対象リソースの特定（タグベース）

`deploy.sh` は全リソースに `scenario=alphafold3-structure-prediction` タグを付与しています。

> [!IMPORTANT]
> **同じサブスクリプションを複数人で使っている場合、他のユーザーの AF3 RG が候補に出ることがあります。** 必ず `owner` タグと目視で自分の RG を確認してから削除してください。

```bash
# タグで候補 RG を列挙 (owner タグも表示)
az group list \
  --query "[?tags.scenario=='alphafold3-structure-prediction' && tags.project=='spread1000'].{name:name, owner:tags.owner, location:location}" \
  -o table
```

出力例:

```
Name                                              Owner                Location
------------------------------------------------  -------------------  ----------
rg-spread1000-alphafold3-structure-prediction-taro   taro@example.ac.jp   japaneast
rg-spread1000-alphafold3-structure-prediction-hana   hana@example.ac.jp   japaneast   ← 他人の RG
```

**必ず自分の RG 名を明示的に指定してください**:

```bash
RG=rg-spread1000-alphafold3-structure-prediction-taro   # ← 自分の RG 名に置き換え

# 一致するか確認
az group show --name "${RG}" \
  --query "{name:name, owner:tags.owner, scenario:tags.scenario}" -o table

# Workspace と Compute Instance を取得
WS=$(az ml workspace list --resource-group "${RG}" --query "[0].name" -o tsv)
CI=$(az ml compute list --resource-group "${RG}" --workspace-name "${WS}" \
  --query "[?type=='computeinstance'].name" -o tsv | head -1)
echo "WS=${WS}  CI=${CI}"
```

---

## 選択肢

### A. 一時停止（当日中にまた使う）

Compute Instance の GPU/CPU 課金だけ止めます。数分で再起動できます。**ディスク・IP 課金は残ります。**

```bash
az ml compute stop \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}"
```

> [!WARNING]
> **`/mnt/af3/public_databases` (~630 GB) は停止と同時に消失します。**
> 再開時は `setup-af3.sh` を再度実行し、DB を再ダウンロードする必要があります（60〜120 分）。
> 頻繁に停止・再開する運用の場合は下記「DB の永続化」を検討してください。

再開:

```bash
az ml compute start \
  --name "${CI}" \
  --resource-group "${RG}" \
  --workspace-name "${WS}"
```

### B. Compute Instance を削除（1 週間〜1 か月使わない）

Workspace は残し、GPU VM だけ削除します。**`/mnt` は当然消えます。**

> [!WARNING]
> **削除前に必ず** 上記「Compute Instance を停止する前にやること」に従い、
> 推論結果を `~/cloudfiles` に退避してください。
> **`af3.bin` は Compute Instance と共に削除されます** — 承認メールから再ダウンロード可能ですが、
> 頻繁に再セットアップする運用ではフォームの再申請を求められる可能性もあります。

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
> **これはリソースグループ内の全リソースを削除します。取り消せません。**
> 実行前に必要な結果を Blob Storage や自分の PC にコピーしてください。
> `af3.bin` を再利用予定なら、ローカル PC に保管しておくこと。

```bash
# 上記「対象リソースの特定」で取得した RG を使う

# 2. リソースグループ内の Key Vault 名を先に控える (削除後にパージするため)
KV_NAMES=($(az keyvault list --resource-group "${RG}" --query "[].name" -o tsv))
# RG のロケーションを取得 (パージには元 Vault のロケーションが必要)
RG_LOCATION=$(az group show --name "${RG}" --query location -o tsv 2>/dev/null || echo "")
echo "対象 Key Vault: ${KV_NAMES[@]:-(なし)} (location: ${RG_LOCATION})"

# 3. リソースグループごと削除 (完了まで 5-15 分)
az group delete --name "${RG}" --yes

# 4. Key Vault はソフト削除保護 (7 日) が残る。放置しても課金は発生しない
for KV in "${KV_NAMES[@]}"; do
  read -rp "Key Vault '${KV}' をパージしますか？ [y/N] " ANS
  if [[ "${ANS}" == "y" ]]; then
    az keyvault purge --name "${KV}" --location "${RG_LOCATION}"
  fi
done
```

> [!CAUTION]
> **`az keyvault list-deleted` を検索して自動パージしてはいけません。** 別プロジェクト・別ユーザーの Vault を巻き込む事故が発生します。必ずリソースグループから取得した名前のみをパージ対象にし、対話確認を挟んでください。

---

## DB の永続化（応用）

`/mnt` の DB は停止で消えるため、以下のいずれかで永続化を検討できます。
**ただし追加コストが発生します。以下は概念設計であり、実装手順は含みません。**

> [!WARNING]
> 以下 3 案はいずれも本クイックスタートでは **手順やスクリプトを提供していません**。
> 実装時は VNet / Private Endpoint / DNS / RBAC / マウントスクリプト等の追加設計が必要です。

### 案 1: Azure Files NFS（機関全体で共有、要 VNet 設計）

- 約 **630 GB Premium NFS ≒ 月 ¥13,000〜¥20,000**（概算）
- 複数の Compute Instance からマウント可能
- **前提**: Azure Files NFS は Private Endpoint または Service Endpoint 経由のみアクセス可能。Compute Instance を VNet 統合するか、Vnet 内に別途 CI を作り直す必要あり (既定の deploy.sh の CI は VNet 統合していません)
- 概略の手順（各ステップに追加設計が必要）:
  1. Storage Account (Premium FileStorage) を作成し NFS 4.1 の Files 共有を作成（700〜1000 GiB）
  2. VNet + Private Endpoint + Private DNS を設定
  3. Compute Instance を同 VNet に配置し、`sudo mount -t nfs` を実行
  4. `setup-af3.sh` の `DB_DIR` をこのマウントポイントに変更

### 案 2: Blob (圧縮) + 起動時 azcopy 転送

- 圧縮された 252 GB を Blob に保管（Hot tier で **月 約 ¥600 (¥2.34/GB × 252 GB)**、Cool tier で **月 約 ¥380 (¥1.50/GB × 252 GB)**、Japan East 2026 年 7 月時点、Azure 料金計算ツールで再確認推奨）
- **前提**: 公式 `fetch_databases.sh` は固定 URL から取得するだけなので、Blob から復元する自前スクリプト（`azcopy copy` + `tar -xzf` 等）を用意する必要があります
- 起動時間が **DL 15〜30 分** に短縮（NVIDIA GPU 課金は待ち時間中も継続する点に注意）

### 案 3: 独立した Azure VM に Managed Disk 添付

- Compute Instance ではなく **通常の Azure VM (NC40ads_H100_v5)** を使う
- 800 GB Premium SSD を添付し永続化（月約 ¥15,000〜¥20,000）
- Azure ML の Jupyter 統合は使えないが、SSH で自由に操作可能
- H100 VM + Managed Disk で **1 か月起動しっぱなしなら 100 万円超**の課金となる点に注意

> [!IMPORTANT]
> **1 か月に数回しか AF3 を使わない場合は永続化コスト > 再ダウンロード時間コスト**になり得ます。
> セッションあたり **60〜120 分の DB 再ダウンロード時間** vs **月額数万円の永続化コスト** を比較してください。

---

## 課金の確認

Azure Portal → **コスト管理 + 請求** → **コスト分析** で、`tags: scenario=alphafold3-structure-prediction` によるフィルタリングが可能です（`deploy.sh` が付与するタグ）。

CLI で確認したい場合は Cost Management REST API を `az rest` で直接叩きます:

```bash
SUB_ID=$(az account show --query id -o tsv)
FROM=$(date -d '30 days ago' -u +%Y-%m-%dT00:00:00Z)
TO=$(date -u +%Y-%m-%dT00:00:00Z)

az rest --method post \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --body "{
    \"type\": \"Usage\",
    \"timeframe\": \"Custom\",
    \"timePeriod\": {\"from\": \"${FROM}\", \"to\": \"${TO}\"},
    \"dataset\": {
      \"granularity\": \"Daily\",
      \"aggregation\": {\"totalCost\": {\"name\": \"Cost\", \"function\": \"Sum\"}},
      \"grouping\": [{\"type\": \"Dimension\", \"name\": \"ResourceGroup\"}]
    }
  }"
```

## 完了チェック

- [ ] 推論結果を `~/cloudfiles` にコピー済み（`TERMS_OF_USE.md` を含む）
- [ ] `af3.bin` の扱いを決定した（削除 or ローカル保管）
- [ ] Compute Instance が **停止** または **削除** 済み
- [ ] （プロジェクト完了時のみ）リソースグループごと削除済み
- [ ] （必要なら）Key Vault のパージが完了
- [ ] Azure Portal の **コスト分析** で当該 RG の当日課金がゼロ／低額になっている

**戻る**: [../README.md](../README.md)
