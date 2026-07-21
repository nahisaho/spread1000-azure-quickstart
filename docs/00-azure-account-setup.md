# 00. Azure アカウント準備

> **対象読者**: SPReAD-1000 採択の研究代表者（Azure 未経験）
> **所要時間**: 30〜90 分（機関の調達フロー次第）
> **前提**: 大学・研究機関のメールアドレスと、機関の調達担当者との連絡経路

このドキュメントは **どのクイックスタートを始める前にも必ず一度読む** ことを想定しています。ここでつまずくと、後段の GPU クォータ申請やコスト管理も進められません。

---

## 1. Azure サブスクリプションの入手方法

Azure の課金単位は **サブスクリプション**（Subscription）です。研究者が使う経路は主に 4 種類あります。

| # | 経路 | 契約主体 | 支払い | SPReAD-1000 での典型例 |
|---|---|---|---|---|
| A | **機関の EA / MCA-E**（Enterprise Agreement / Microsoft Customer Agreement — Enterprise） | 大学法人 | 請求書（後払い） | 大規模大学の情報基盤センター経由 |
| B | **CSP**（Cloud Solution Provider 経由） | 販社 → 大学 | 販社の請求書 | 中規模大学が地元 SIer 経由で契約 |
| C | **従量課金**（Pay-As-You-Go） | 研究代表者個人 or 研究室 | クレジットカード | 少額の PoC、個人での試用 |
| D | **Azure for Students** / **Azure Sponsorship** | 個人 | クレジット付与 | 学生・共同研究者の学習用（本番課題には不可） |

> [!IMPORTANT]
> **SPReAD-1000 の研究費で支払う場合は、必ず所属機関の会計担当者・情報基盤センターに事前確認してください。** 個人カードで先に契約すると、後から機関の EA サブスクリプションに移管できない場合があります。

### 1.1 まず確認すべきこと

- 所属機関に既存の Azure EA / MCA テナントが存在するか（`.onmicrosoft.com` テナント名 or 独自ドメイン）
- 存在する場合、**新規サブスクリプションを研究室単位で払い出せる**か（多くの機関は「研究者ごとに 1 サブスク」を推奨）
- 存在しない場合、機関として MCA-E を締結するか、CSP 経由にするかを決める必要がある

### 1.2 「まず動かしたい」なら従量課金で開始する

- MEXT の研究費で費用を建て替える場合は機関ルールを確認してから
- クレジットカード + 円建て請求で個人契約可能: <https://azure.microsoft.com/ja-jp/pricing/purchase-options/pay-as-you-go/>
- **本番課題実行前に必ず機関のサブスクリプションへ移行する**（従量課金のままだと決算処理が煩雑）

---

## 2. テナント / サブスクリプション / リソースグループの関係

Azure の階層構造を理解しないと、権限エラーで詰まります。

```
Microsoft Entra テナント（旧 Azure AD）
  └─ 管理グループ（任意）
      └─ サブスクリプション（=課金単位）★ 各クイックスタートで 1 つ用意
          └─ リソースグループ（=削除の単位）★ 各シナリオで 1 つ
              └─ リソース（VM / ストレージ / AML ワークスペース など）
```

- **テナント**: 認証基盤。1 機関 = 1 テナントが基本。
- **サブスクリプション**: 課金明細と RBAC 権限の境界。**研究室単位で 1 つ**を基本にし、その中でシナリオごとに RG を分けます。サブスクを増やしすぎるとコスト集計・quota 申請・請求書処理が煩雑になります（機関の会計処理単位に合わせるのが最も安全）。
- **リソースグループ**: 論理的まとまり。**クイックスタート終了時に丸ごと削除**する運用が原則。**シナリオ = RG 1 個** を厳守します。

> [!TIP]
> 各クイックスタートの `99-cleanup` は「リソースグループを消せば全て消える」設計です。**RG は必ずシナリオ専用で新規作成**してください。既存 RG に相乗りすると誤って他のリソースを削除する恐れがあります。

---

## 3. 必要な権限（RBAC ロール）

各クイックスタートで必要な最低権限は以下です。

| 操作 | 必要ロール | 付与範囲 |
|---|---|---|
| リソースグループ作成 | `Contributor` | サブスクリプション |
| Bicep / Terraform でリソース一括作成 | `Contributor` | サブスクリプション（または RG） |
| マネージド ID にロール付与 | `User Access Administrator` または `Role Based Access Control Administrator` | RG（対象範囲に合わせて） |
| リソースプロバイダー登録（初回のみ） | `Contributor` | サブスクリプション |
| Azure Policy 割当て（タグ強制など） | `Resource Policy Contributor` | サブスクリプション |
| 予算アラート作成 | `Cost Management Contributor` | サブスクリプション |
| Azure OpenAI / Azure AI Foundry 利用申請 | `Cognitive Services Contributor` | サブスクリプション |

> [!IMPORTANT]
> **最小権限の原則**: 実運用では **`Contributor` + `User Access Administrator` (または `Role Based Access Control Administrator`)** の 2 ロール併用で本リポジトリのクイックスタートは完走できます。`Owner` は「Contributor + User Access Administrator を包含する強い権限」なので、機関ポリシーで許可される場合の学習・PoC に限れば手っ取り早いですが、**多くの大学では研究者への Owner 付与が制限**されています。その場合は上記 2 ロールの組み合わせを機関の管理者に依頼してください。

### 3.1 権限の確認

```bash
# サインイン中ユーザーの Object ID を取得
MY_OID=$(az ad signed-in-user show --query id -o tsv)
SUB_SCOPE="/subscriptions/$(az account show --query id -o tsv)"

# 直接割当だけでなく、グループ経由・上位スコープからの継承ロールも含めて一覧
az role assignment list \
  --assignee "$MY_OID" \
  --scope "$SUB_SCOPE" \
  --include-inherited \
  --include-groups \
  --output table
```

出力例:

```
Principal                        Role                        Scope
-------------------------------  --------------------------  ------------------------------------------
user@example.ac.jp               Contributor                 /subscriptions/xxxxxxxx-...-xxxxxxxxxxxx
user@example.ac.jp               User Access Administrator   /subscriptions/xxxxxxxx-...-xxxxxxxxxxxx
```

> [!TIP]
> **`--include-inherited --include-groups` を必ず付ける**こと。これらを省略すると管理グループやセキュリティグループ経由で付与されたロールが表示されず、「権限あるのに見えない」誤解を招きます。

---

## 4. Azure CLI のインストールとサインイン

各クイックスタートは **Azure CLI 2.60 以降** を前提とします。

### 4.1 インストール

| OS | コマンド |
|---|---|
| Ubuntu / WSL2 | `curl -sL https://aka.ms/InstallAzureCLIDeb \| sudo bash` |
| macOS | `brew install azure-cli` |
| Windows | `winget install -e --id Microsoft.AzureCLI` |

インストール後の確認:

```bash
az --version | head -3
# azure-cli                         2.65.0
# core                              2.65.0
# telemetry                          1.1.0
```

> [!NOTE]
> **バージョンが 2.60 未満の場合は `az upgrade` を実行**してください。古い CLI は AML v2 (`az ml`) や Bicep が動かないことがあります。

### 4.2 拡張機能

クイックスタートで使う主な拡張:

```bash
az extension add --name ml           # Azure Machine Learning
az extension add --name application-insights
az extension update --name ml        # 定期的に更新
```

### 4.3 サインイン

```bash
# ブラウザで既定ログイン
az login

# ヘッドレス環境（WSL2, リモート SSH など）ではデバイスコード
az login --use-device-code

# 機関テナントを指定してログイン（マルチテナント所属時）
az login --tenant contoso.onmicrosoft.com
```

サインイン後、使用するサブスクリプションを固定します:

```bash
# サブスクリプション一覧
az account list --output table

# 使うサブスクを既定に設定
az account set --subscription "SPReAD-1000-<PI 名>"

# 確認
az account show --query "{name:name, id:id, tenantId:tenantId}" -o json
```

> [!IMPORTANT]
> 各クイックスタート内のコマンドは **`az account show` で表示される既定サブスクリプション** に対して実行されます。**複数サブスクを持つ人は、シナリオ開始前に必ず `az account set` してください。**

---

## 5. リソースプロバイダーの登録

Azure は使用するサービスの「プロバイダー」を初回のみ登録する必要があります。SPReAD-1000 の各クイックスタートで必要なものをまとめて登録します。

```bash
for RP in \
  Microsoft.Compute \
  Microsoft.Storage \
  Microsoft.Network \
  Microsoft.KeyVault \
  Microsoft.ContainerRegistry \
  Microsoft.ContainerService \
  Microsoft.Batch \
  Microsoft.MachineLearningServices \
  Microsoft.CognitiveServices \
  Microsoft.OperationalInsights \
  Microsoft.Insights ; do
  az provider register --namespace "$RP" --wait
  echo "Registered: $RP"
done
```

**所要時間**: 各プロバイダー 30 秒〜3 分。合計 5〜10 分。

> [!TIP]
> `--wait` を付けないと非同期実行になり、後続の `az deployment` が「プロバイダー未登録」エラーで失敗します。必ず `--wait` を付けるか、次の確認コマンドで `Registered` になるまで待ってください。

登録状況の確認:

```bash
az provider list --query "[?namespace=='Microsoft.MachineLearningServices'].{ns:namespace, state:registrationState}" -o table
```

---

## 6. Microsoft Entra（旧 Azure AD）関連

### 6.1 多要素認証（MFA）

- **必須**: 機関の設定で MFA が強制されている場合、`az login` の途中で Microsoft Authenticator アプリの承認を求められます
- **CI/CD 用途**: 人間の MFA では非対話実行できないので、後述のサービスプリンシパルを使います

### 6.2 条件付きアクセス（Conditional Access）

一部の機関では「学内 IP からのみ Azure Portal にアクセス可」といった条件付きアクセスが設定されています。**自宅 / 出張先から `az login` できない場合は情報基盤センターに相談**してください。

### 6.3 サービスプリンシパル（自動化用アカウント）

CI/CD や無人ジョブで使う「マシン用 ID」です。各クイックスタートは対話ログインを前提としていますが、自動化する場合は:

```bash
az ad sp create-for-rbac \
  --name "sp-spread1000-<PI 名>" \
  --role Contributor \
  --scopes "/subscriptions/$(az account show --query id -o tsv)"
```

出力の `appId`, `password`, `tenant` を安全な場所（Key Vault, GitHub Secrets など）に保管してください。**平文でリポジトリにコミットしない**こと。

---

## 7. サポートプランと問い合わせ窓口

| プラン | 月額 | 対応時間 | 推奨対象 |
|---|---:|---|---|
| Basic | 無料 | 24×7（請求のみ） | 学習・PoC |
| Developer | $29〜 | 平日 8 時間 | 個人開発者 |
| **Standard** | $100〜 | 24×7、初回応答 1 時間 | 研究プロジェクト（推奨） |
| Professional Direct | $1,000〜 | 24×7、初回 1 時間、TAM 付き | 全学基盤 |

> [!NOTE]
> **GPU クォータ増加申請は Basic プランでも可能** ですが、**リソースが動かない・障害が疑われる問い合わせには Developer 以上が必要**です。SPReAD-1000 のような期限付き研究では Standard 加入を検討してください（クイックスタート全体を通じて発生する GPU 課金額に比べれば十分に安価）。

---

## 8. 完了チェックリスト

次のステップに進む前に、以下がすべて YES になっていることを確認してください。

- [ ] 所属機関の Azure 契約経路（EA / CSP / PAYG）を特定した
- [ ] 使用するサブスクリプション名を決めた（例: `spread1000-<PI 名>`）
- [ ] そのサブスクリプションで自分に `Contributor` + `User Access Administrator`（または `Owner`）が付与されている（`az role assignment list` で確認）
- [ ] `az login` に成功し、`az account show` で正しいサブスクが表示される
- [ ] リソースプロバイダーを一括登録した（Section 5）
- [ ] コスト管理: `docs/01-cost-management.md` を読み、予算アラートを設定した
- [ ] GPU シナリオを実行する場合: `docs/02-gpu-quota.md` を読み、必要な GPU quota を申請した

---

## 9. トラブルシューティング

| 症状 | 原因 | 対応 |
|---|---|---|
| `az login` がブラウザを開かない | WSL2 / SSH 等の GUI 無し環境 | `az login --use-device-code` |
| `az login` 後もサブスクが見えない | 別テナントに存在 | `az login --tenant <テナント ID>` |
| `AuthorizationFailed` エラー | RBAC 権限不足 | Section 3 を参照、機関の管理者に `Contributor` + `User Access Administrator` の付与を依頼 |
| `MissingSubscriptionRegistration` | RP 未登録 | Section 5 を再実行 |
| `az` コマンドが見つからない | パス未設定 | シェル再起動 or `source ~/.bashrc` |
| `az upgrade` が失敗 | パッケージマネージャ経由でインストール | 各 OS の手順で再インストール |

---

## 次のドキュメント

- **[01-cost-management.md](01-cost-management.md)** — 予算アラート・タグ戦略・GPU コスト最適化
- **[02-gpu-quota.md](02-gpu-quota.md)** — GPU SKU 選定と quota 申請
