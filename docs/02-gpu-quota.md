# 02. GPU クォータ申請

> **対象読者**: SPReAD-1000 採択の研究代表者（Azure 未経験）
> **所要時間**: 申請自体 15 分 + Microsoft 側承認 1〜5 営業日
> **前提**: [`00-azure-account-setup.md`](00-azure-account-setup.md) と [`01-cost-management.md`](01-cost-management.md) を完了していること

Azure の GPU VM は**新規サブスクリプションではデフォルト quota が 0**です。**必ず事前に quota 増加申請**してから、GPU シナリオ（AlphaFold 3 / BioEmu / ESMFold / MONAI / TamGen 等）に着手してください。

---

## 1. SPReAD-1000 で使う主な GPU SKU

各クイックスタートで想定する SKU は以下です。詳細は各シナリオ README を参照してください。

| クイックスタート | 推奨 SKU | GPU | GPU メモリ | vCPU | Quota family（申請単位） |
|---|---|---|---:|---:|---|
| TamGen | `Standard_NC4as_T4_v3` | T4 x1 | 16 GB | 4 | `standardNCASv3T4Family` |
| ESMFold | `Standard_NC24ads_A100_v4` | A100 x1 | 80 GB | 24 | `standardNCADSA100v4Family` |
| AlphaFold 3 | `Standard_NC24ads_A100_v4` | A100 x1 | 80 GB | 24 | `standardNCADSA100v4Family` |
| BioEmu | `Standard_NC24ads_A100_v4` | A100 x1 | 80 GB | 24 | `standardNCADSA100v4Family` |
| MONAI 3D | `Standard_NC4as_T4_v3` または `Standard_NC24ads_A100_v4` | T4 or A100 | 16 / 80 GB | 4 / 24 | 同上 2 種 |
| RNA-Seq | GPU 不要（Azure Batch CPU） | — | — | — | — |

> [!IMPORTANT]
> **quota は「vCPU 数」単位で管理**されます。SKU 名ではなく **`vCPU × 同時実行数`** で申請してください。例: `Standard_NC24ads_A100_v4` を 2 台同時に使うなら `24 × 2 = 48 vCPU` を申請します。

---

## 2. Japan East / Japan West の GPU 提供状況（傾向）

GPU の**リージョン別提供状況・在庫は日次で変動**します。ここに固定表を載せると陳腐化が早いため、**必ず実サブスクリプションで下記コマンドを実行して確認**してください。

一般的な傾向（2026 年半ば時点）としては次の通りです（あくまで目安、正式な情報は Azure Portal と価格ページを一次資料としてください）:

| SKU family | Japan East | Japan West | 代替リージョン候補 |
|---|:---:|:---:|---|
| NCASv3-T4 (T4) | ○ | ○ | Korea Central, Southeast Asia |
| NCadsA100v4 (A100 80GB) | ○ | △ | Korea Central, Sweden Central, Australia East |
| NCadsH100v5 (H100) | ○ | ✗ | Sweden Central, East US 2, South Central US |
| ND 系マルチ GPU（A100 x8 / H100 x8 など） | ✗ / △ | ✗ | East US 2, Sweden Central, South Central US |

**凡例（傾向）**: ○ 契約サブスクで多くの場合利用可 / △ 一部のサブスクや期間のみ / ✗ 一般には未提供

> [!TIP]
> **Japan East で在庫が取れない場合の第一選択は Korea Central**（レイテンシ差が最も小さい）です。次点で Sweden Central または East US 2。**Storage / AML ワークスペースも同じリージョンに揃える**ことを忘れないでください（別リージョンは egress 課金 + 転送レイテンシ増）。

### 2.1 各リージョンでの SKU 提供確認（サブスク単位で必須）

```bash
REGION=japaneast
az vm list-skus --location $REGION --resource-type virtualMachines \
  --query "[?family=='standardNCADSA100v4Family'].{name:name, size:size, family:family, restrictions:restrictions}" \
  -o json
```

**結果の読み方**:

- `restrictions` が **空配列 `[]`** → そのサブスクリプションでその SKU をそのリージョンにデプロイ可能（ただし**当日の在庫まで保証するものではない**）
- `restrictions[].reasonCode` が **`NotAvailableForSubscription`** → そのサブスクで無効化（quota 申請で解放される場合と、そもそも提供されない場合がある）
- `restrictions[].reasonCode` が **`QuotaId`** など他の理由 → 特定のオファータイプ・ゾーンなどで制限。詳細は `restrictions[].values` に対象ゾーン等が入る

> [!WARNING]
> **`restrictions` が空でも「在庫あり」を保証しません。** SKU 一覧は「そのサブスクで作成できる可能性がある」ことを示すだけで、実際の作成時にリージョン全体のキャパシティ不足で `AllocationFailed` になることがあります。作成に失敗した場合はゾーン変更・別リージョンを試してください。

---

## 3. 現在の quota を確認 — **「直接 VM」と「AML compute」は別ワークフロー**

本リポジトリのクイックスタートでは 2 つのデプロイパスがあります:

- **A. 直接 VM を作るシナリオ**（TamGen / ESMFold の bare VM モードなど）→ サブスクリプションの Compute quota を使用
- **B. Azure Machine Learning のコンピュートクラスタで動かすシナリオ**（AlphaFold 3 / BioEmu / MONAI 等）→ **AML compute 専用 quota** を使用

**どちらを使うか事前に決めた上で、対応する quota を確認・申請**してください。両方使う場合は両方の quota が必要です。

### 3.1 A: 直接 VM の Compute quota（`az vm list-usage`）

```bash
REGION=japaneast

# Compute quota 全体
az vm list-usage --location $REGION -o table

# 特定 family だけ抽出（A100 の例）
az vm list-usage --location $REGION \
  --query "[?contains(name.value, 'NCADSA100v4')].{family:localName, current:currentValue, limit:limit}" \
  -o table
```

出力例（新規サブスクの典型）:

```
Family                          Current    Limit
------------------------------  ---------  -------
Standard NCADSv3 T4 Family      0          0
Standard NCADSA100_v4 Family    0          0
Standard NCADSH100_v5 Family    0          0
Total Regional vCPUs            0          10
```

> [!WARNING]
> **`Total Regional vCPUs` が個別 family より小さいと、family quota があっても VM が作れません。** SKU family quota と `Total Regional vCPUs` の**両方**を申請する必要があります。

### 3.2 B: AML compute 専用の quota（`az ml compute list-usage`）

AML compute クラスタ / インスタンスは **サブスクの直接 VM quota とは独立**した quota で管理されます。**既に AML ワークスペースが存在するリージョン**で下記を実行します（各シナリオの `02-provision-aml` を実行済みであることが前提）:

```bash
RG="spread1000-<シナリオ名>"
WS="spread1000-<シナリオ名>-ws"
REGION="japaneast"

az ml compute list-usage \
  --resource-group "$RG" \
  --workspace-name "$WS" \
  --location "$REGION" \
  -o table
```

出力例（AML の quota は `Standard_NC24ads_A100_v4` のような SKU 名でも表示されます）:

```
Name                                Type    LocalizedValue                        CurrentValue    Limit    Unit
----------------------------------  ------  ------------------------------------  --------------  -------  -----
Standard NC A100 v4 Family Cluster  Count   Standard NC A100 v4 Family Cluster    0               0        Count
Total Cluster Dedicated Regional…   Count   Total Cluster Dedicated Regional …    0               24       Count
```

> [!IMPORTANT]
> - **AML 側で `Total Cluster Dedicated Regional vCPUs` と個別 SKU family quota の両方**が上限として効きます。
> - **AML の quota は特定のワークスペース経由で照会**します（`--resource-group` と `--workspace-name` が必須）。まだワークスペースが無い場合は、代表シナリオの `02-provision-aml` を先に流してから確認してください。
> - **AML compute でジョブを回すクイックスタート（AlphaFold 3、BioEmu、MONAI 等）は、Section 3.1 の直接 VM quota を増やしても効果がありません。** 必ず AML 側の quota を申請してください。

### 3.3 Spot（Low priority）quota も別枠

**Spot は PAYG とは別枠**の quota です。Spot 中心の運用なら Spot quota も申請してください。

- **直接 VM の Spot vCPU quota**: 各リージョンに **family 横断の統合された「Spot vCPUs」総枠が 1 つ**あります（family 別ではありません）。Azure Portal の **サブスクリプション → Usage + quotas** で `Compute` を選び、`Spot` でフィルタして確認・申請します。CLI では `az quota list --scope "/subscriptions/$(az account show --query id -o tsv)/providers/Microsoft.Compute/locations/$REGION"` で確認できます（`az extension add --name quota` が必要）。
- **AML compute の low-priority quota**: `az ml compute list-usage` の出力に `Total Cluster LowPriority Regional vCPUs` などの独立した項目として表示されます（Section 3.2 と同じコマンドで確認可）。

> [!WARNING]
> 直接 VM の Spot と AML の low-priority は**別々のリソースプロバイダー配下の別 quota** です。どちらを使うかに応じて対応する quota を確認・申請してください。

---

## 4. Quota 増加申請の手順（推奨: Azure Portal）

### 4.1 Portal から申請（初心者に最も安全）

1. Azure Portal → **Subscriptions** → 対象サブスクリプションを選択
2. 左ペイン **Settings** → **Usage + quotas**
3. **Provider** で `Compute` を選択、**Location** で `Japan East` などを選択
4. 対象の family（例: `Standard NCADSA100_v4 Family`）で **Request increase**（右端の鉛筆アイコン）
5. **New limit** に希望 vCPU 数を入力（例: `48` = A100 x2 台分）
6. **Submit** → サポートケースが自動生成される

> [!IMPORTANT]
> **`Total Regional vCPUs` も別途申請**してください。手順は同じ（Provider: Compute、"Total Regional vCPUs" を選択）。

### 4.2 CLI で申請（AML compute の場合）

AML compute の quota 増加は **Azure Portal → 各ワークスペース → Compute → Quota** から申請するのが最も確実です（背後で `Microsoft.Support` のサポートケースが作成されます）。CLI では以下いずれかを使えます:

- **`az support in-subscription tickets create`**（サポート拡張、`az extension add --name support` が必要）で `Quota` タイプのケースを起こす
- Portal 画面右上「Request quota」→ 自動生成されたサポートリクエストで送信

> [!NOTE]
> かつて存在した `az ml workspace update-quotas` サブコマンドは AML CLI v2 では廃止・非提供です。**古いドキュメントやブログ記事に載っていても現行 CLI では動きません。**Portal 経由の申請を第一選択にしてください。

### 4.3 申請時に書くべき情報

サポートリクエスト画面で「詳細説明」に以下を含めると承認が早くなります（日本語 or 英語で可）:

```
Purpose: MEXT SPReAD-1000 grant research project (2026 fiscal year)
Workload: [AlphaFold 3 / BioEmu / MONAI 等の具体名]
Peak concurrency: 2 concurrent A100 VMs for 4 hours per experiment
Duration: 2026-08 〜 2027-03（研究期間）
Region rationale: Data residency in Japan (patient data / consortium agreement)
```

> [!NOTE]
> **単に「増やしてください」だけだと差し戻される**ことがあります。用途・期間・並列数を書くと 1〜2 営業日で承認されることが多いです。

### 4.4 承認までの目安

| 申請規模 | 承認までの目安 |
|---|---|
| A100 x1〜4 相当（24〜96 vCPU） | 数時間〜1 営業日 |
| A100 x8〜16 相当（192〜384 vCPU） | 1〜3 営業日 |
| H100 大規模（96〜768 vCPU） | 3〜10 営業日、担当者と個別調整あり |

**承認後、CLI に反映されるまで最大 15 分ラグ**があります。すぐに `az vm create` して失敗しても慌てず、15 分待って再実行してください。

---

## 5. Quota が取れない時の代替戦略

### 5.1 別リージョンへフォールバック

Japan East で在庫が取れない場合の推奨順:

1. **Korea Central**（レイテンシ差が最も小さい、〜30ms）
2. **Sweden Central**（欧州、GPU 在庫が潤沢、〜250ms）
3. **East US 2**（GPU 種類が最も多い、〜160ms）
4. **Australia East**（アジア圏、〜120ms）

> [!WARNING]
> データを海外リージョンに移す場合、機関の**データ持ち出しポリシー**（特に臨床データ・共同研究契約）を必ず事前確認してください。医用画像などは Japan 内での処理が必須の場合があります。

### 5.2 小さい SKU で分割

A100 x8 の ND シリーズ（`Standard_ND96asr_v4` など）が該当リージョンで提供・quota 発行されない場合、A100 x1 (`Standard_NC24ads_A100_v4`) を 8 台並列で回す方が quota が取りやすいです（ただし通信オーバーヘッドあり、モデル並列は非対応）。

### 5.3 Spot に切り替え

PAYG quota が取れない場合、**Spot quota は別枠で緩い**傾向があります。学習・大規模計算では Spot + チェックポイントの構成で十分です（[`01-cost-management.md`](01-cost-management.md) §6.1 参照）。

### 5.4 Azure Batch を検討

シミュレーションや RNA-Seq のような embarrassingly parallel なワークロードは、**Azure Batch の Low-priority VM プール**が別枠 quota で運用でき、大量並列に向いています（[`research-fields/life-pharma-science/04-transcriptomics-rnaseq/`](../research-fields/life-pharma-science/04-transcriptomics-rnaseq/) 参照）。

---

## 6. GPU SKU 選定ガイド（研究者向け早見表）

### 6.1 「まず動かしたい」場合

| 状況 | 推奨 SKU | 理由 |
|---|---|---|
| ワークショップ・PoC | `Standard_NC4as_T4_v3` | 最も quota が取りやすい、1 時間 ~$0.5 |
| タンパク質構造予測（小さめタンパク） | `Standard_NC24ads_A100_v4` | 80GB メモリで多くのタンパクが乗る |
| LLM 推論（〜13B） | `Standard_NC24ads_A100_v4` | 80GB で 13B FP16 が動く |

### 6.2 「本番回したい」場合

| 状況 | 推奨 SKU | 理由 |
|---|---|---|
| LLM 学習・fine-tune（〜70B） | `Standard_NC96ads_A100_v4` (A100 x4) | 80GB x4 = 320GB |
| 大規模事前学習 | ND シリーズ（`Standard_ND96asr_v4` = A100 x8 / `Standard_ND96isr_H100_v5` = H100 x8 等）※提供リージョン限定 | InfiniBand で multi-node |
| 推論スループット重視 | `Standard_NC40ads_H100_v5` | H100 x1、A100 の 2〜3 倍速 |

### 6.3 選ぶべきでない SKU

| SKU | 理由 |
|---|---|
| `Standard_NV*` シリーズ（旧世代） | remote 3D 表示向け、AI/HPC には非効率 |
| `Standard_NC6` (K80、v1) | 廃止予定、Compute Capability 3.7 で PyTorch 2.x 動作せず |
| M シリーズ（メモリ最適化） | GPU 非搭載 |

---

## 7. 完了チェックリスト

- [ ] シナリオで使う SKU family と必要 vCPU 数を特定した
- [ ] シナリオが「直接 VM」パスか「AML compute」パスかを特定した
- [ ] （直接 VM）`az vm list-usage` で現在の quota を確認した
- [ ] （AML）`az ml compute list-usage -g "$RG" -w "$WS" -l "$REGION"` で AML 側の quota を確認した
- [ ] 不足分について Portal から quota 増加申請した
- [ ] （直接 VM）`Total Regional vCPUs` も忘れず申請した
- [ ] （AML）`Total Cluster Dedicated Regional vCPUs` も忘れず申請した
- [ ] Spot 中心運用なら Spot 用 quota も別途申請した
- [ ] 承認メールを受領し、`az vm list-usage` / `az ml compute list-usage` で `Limit` が反映されている

---

## 8. トラブルシューティング

| 症状 | 原因 | 対応 |
|---|---|---|
| `SkuNotAvailable` | リージョンで SKU 未提供 or 在庫切れ | Section 2.1 で提供確認、別リージョンへ |
| `QuotaExceeded` / `OperationNotAllowed` | quota 不足 | Section 4 で申請 |
| quota 承認済みだが VM 作成失敗 | 反映に最大 15 分ラグ | 待ってから再実行 |
| AML ジョブが `NotEnoughQuota` で pending | AML compute 専用 quota 不足 | Section 3.2 & 4.2 |
| Spot VM が即 evict | 該当リージョン・SKU の需要逼迫 | 別リージョン、または PAYG に切り替え |
| `Total Regional vCPUs exceeded` | family quota はあるが総枠不足 | Total Regional vCPUs も申請 |
| Portal で "Request increase" が押せない | 対象 SKU が「調整不可 quota」に該当 / サブスクがサポート対象外の Free Trial 系 / 権限不足（`Quota Request Operator` 相当が必要） | サブスクの種類とサポート対象性を確認、上位管理者に権限付与を依頼、または Portal のサポートリクエストから手動で新規ケースを起票 |

---

## 9. 参考リンク

- Azure VM SKU 一覧（GPU）: <https://learn.microsoft.com/ja-jp/azure/virtual-machines/sizes-gpu>
- Azure リージョン別サービス提供: <https://azure.microsoft.com/ja-jp/explore/global-infrastructure/products-by-region/>
- Azure quota 一般ドキュメント: <https://learn.microsoft.com/ja-jp/azure/quotas/>
- Compute quota 増加申請: <https://learn.microsoft.com/ja-jp/azure/azure-portal/supportability/per-vm-quota-requests>
- Azure Machine Learning quota: <https://learn.microsoft.com/ja-jp/azure/machine-learning/how-to-manage-quotas>

---

## 各クイックスタートへ戻る

- [🧬 生命科学・薬学](../research-fields/life-pharma-science/)
- [🩺 臨床科学](../research-fields/clinical-science/)
