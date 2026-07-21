# 01. 事前準備

このクイックスタートを完走するために必要な事前手続きです。**すべて完了してから 02 に進んでください。**

## 1. Azure サブスクリプションと権限

- **必須**: Azure サブスクリプションで `Contributor` + `User Access Administrator`（または `Owner`）
- 参照: [`../../../../docs/00-azure-account-setup.md`](../../../../docs/00-azure-account-setup.md)

## 2. リソースプロバイダー登録

```bash
for RP in Microsoft.CognitiveServices Microsoft.Search Microsoft.Storage \
          Microsoft.KeyVault Microsoft.OperationalInsights Microsoft.Insights; do
  az provider register --namespace "$RP" --wait
done
```

## 3. Azure OpenAI 利用申請（Limited Access 対象の場合のみ）

**大半の一般用途では新規申請は不要**になっています（2024 年後半以降、一般的な GA モデルへのアクセスは既定で有効）。以下に該当する場合のみ、Limited Access の申請フォームから承認を得てください:

- 特定の Limited Access 機能（Whisper、GPT-image、動画、Realtime 等の一部）を使う
- 特殊な業種・用途で追加審査が求められる

- 申請フォーム（該当する場合）: <https://aka.ms/oai/access>
- 医療研究用途なら、目的欄に「MEXT SPReAD-1000 grant research (clinical text NLP with synthetic/de-identified data only, IRB-approved)」のように具体的に記入

**利用可否の確認方法**は、次のセクション 4 で対象リージョンのモデル一覧に `gpt-4o` が出るかどうかで判定してください（`account list-kinds` は「サブスクで OpenAI kind の Cognitive Services リソースが作れるか」を示すだけで、モデル承認可否そのものは判定できません）。

## 4. 利用可能なモデル・リージョンを確認

現在の Azure OpenAI モデル提供状況とリージョンを確認します（**日次で変動**）:

```bash
REGION=japaneast
az cognitiveservices account list-models \
  --resource-group dummy-rg-for-model-check --name dummy 2>/dev/null || \
  az cognitiveservices model list --location "$REGION" \
    --query "[?kind=='OpenAI'].{model:model.name, version:model.version, sku:model.skus[0].name, capacity:model.skus[0].capacity.default}" \
    -o table
```

本 quickstart で使用するモデル:

| モデル | 用途 | 想定リージョン | Fallback |
|---|---|---|---|
| `gpt-4o` (2024-11-20 以降) | 質問応答（generation） | Japan East | Sweden Central, East US 2 |
| `text-embedding-3-large` | ベクトル化（embedding） | Japan East | Sweden Central |

> [!IMPORTANT]
> **Japan East でモデル提供が確認できなかった場合は、Sweden Central / East US 2 へフォールバック**してください（Storage / AI Search も同じリージョンに揃える）。**本 quickstart は合成データ動作確認専用**のため、リージョン制約は在庫だけを見て選んで問題ありません。実患者データを扱う別テンプレート（本 quickstart のスコープ外）では法令・機関ポリシーに従ってリージョンを決定してください。

## 5. Azure OpenAI クォータ

Azure OpenAI は **1 分あたりの token 数（TPM）** と **1 分あたりのリクエスト数（RPM）** で quota が管理されます。新規サブスクの既定値は以下:

| モデル | 既定 TPM | 既定 RPM |
|---|---:|---:|
| gpt-4o (Standard) | 30,000 | 180 |
| text-embedding-3-large | 350,000 | 2,100 |

本 quickstart の合成データ規模（数十件のカルテ）では既定 quota で十分です。**大規模データや複数同時研究者で使う場合のみ**、Azure Portal → Azure OpenAI リソース → **Quotas** から増加申請してください（[`../../../../docs/02-gpu-quota.md`](../../../../docs/02-gpu-quota.md) 参照 — GPU quota とは別枠）。

## 6. 実患者データ（PHI）は本 quickstart では扱いません

> [!WARNING]
> **本 quickstart のテンプレートは合成データ動作確認専用**です。次の理由から、実患者データ（PHI: Protected Health Information）は 1 件たりとも投入しないでください。
>
> - AI Search・Azure OpenAI・Blob Storage の**エンドポイントが公開ネットワーク（Public）**に開いている（Private Endpoint 未構成）
> - **Customer Managed Key（CMK）** による保存時暗号化を使用していない
> - Azure OpenAI の **abuse monitoring オプトアウト（modified abuse monitoring）** が申請されていない前提
> - **IRB 審査・機関 CIO 承認・患者同意取得**などのガバナンス手続きが未実施
> - 監査ログ（Log Analytics）は有効だが**院内監査要件を満たす保管期間・アクセス制御は未設定**
>
> 実患者データを扱う本番構成は本 quickstart のスコープ外です。改正個人情報保護法 (2025)、厚労省「医療情報システムの安全管理に関するガイドライン第 6.0 版」、3 省 2 ガイドライン (2023) を満たす別テンプレートを機関の情報セキュリティ担当と共同で設計してください。

## 7. ローカル環境

```bash
python3 --version   # 3.10 以上
pip --version
az --version | head -1
```

Python 依存ライブラリのインストール:

```bash
cd research-fields/clinical-science/02-ehr-nlp-rag
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install \
  "openai>=1.60.2,<2.0" \
  "azure-search-documents==11.5.2" \
  "azure-identity>=1.19.0" \
  "azure-storage-blob>=12.23.1" \
  "python-dotenv>=1.0.1" \
  "tiktoken>=0.8.0"
```

## 8. 変数の設定

以下のシェル変数を `.env` に保存（`inputs/.env.example` をコピー）:

```bash
cp inputs/.env.example .env
# エディタで .env を開き、下記を埋める
```

`.env`（例）:

```
LOCATION=japaneast
RG=spread1000-ehr-nlp
PROJECT_TAG=spread1000
SCENARIO_TAG=ehr-nlp
PI_TAG=yamada-taro
# 下の UNIQUE_SUFFIX は「.env に書き込む固定リテラル値」です（コマンド置換ではありません）。
# 一度だけ生成して固定してください。02-provision.md の手順で自動生成・書き戻しも可能。
# 手動なら別ターミナルで `openssl rand -hex 3` を実行し、その出力（例: a3f9c2）をコピペします。
UNIQUE_SUFFIX=a3f9c2
```

> [!IMPORTANT]
> `.env` は `set -a && source .env && set +a` で毎回読み込まれます。値の右辺に `$(...)` などのコマンド置換を書くと**読み込むたびに再実行され、UNIQUE_SUFFIX が変わって別リソースを作ってしまう**ため必ず固定リテラル（例: `UNIQUE_SUFFIX=a3f9c2`）にしてください。

> [!TIP]
> `.env` は `.gitignore` に含めてリポジトリにコミットしないこと。同梱の `.gitignore` で除外済みです。

## 完了確認

- [ ] Azure サブスクで `Contributor` + `User Access Administrator` を持っている
- [ ] （Limited Access 機能を使う場合のみ）Azure OpenAI 利用申請が承認済み
- [ ] `az cognitiveservices model list` で `gpt-4o` と `text-embedding-3-large` が対象リージョンで見える
- [ ] Python 3.10+ と Azure CLI 2.60+ がインストール済み
- [ ] **本 quickstart で実患者データを扱わないことを理解している**（PHI は §6 の別テンプレートで扱う）
- [ ] `.env` を作成し、変数を埋めた

→ **[02-provision.md](02-provision.md) に進む**
