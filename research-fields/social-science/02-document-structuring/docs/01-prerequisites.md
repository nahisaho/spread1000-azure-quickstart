# 01 — 事前準備

## シェル環境

- **Windows**: WSL2 (Ubuntu 22.04+) — PowerShell では動きません
- **macOS**: 標準 zsh / bash
- **Linux**: 標準 bash
- **Azure Cloud Shell**: ブラウザで即実行可

## Azure CLI

```bash
az version
# azure-cli >= 2.60.0

az login
az account set --subscription "<Subscription 名 or ID>"
az account show -o table
```

## リージョン選定

このシナリオは **`japaneast`** を既定にしています。Document Intelligence と Azure OpenAI (Regional) の両方が利用可能です。

## Azure OpenAI 利用について

`gpt-5.4-mini` は GA モデルであり、追加の申請は不要です。Limited Access モデル (o1-preview ファミリー等) を使う場合は <https://aka.ms/oai/access> から申請してください。

## Resource Provider の登録

```bash
az provider register --namespace Microsoft.CognitiveServices --wait
```

## Python 環境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

pip install -r requirements.txt
```

> [!NOTE]
> `requirements.txt` のバージョンに固定しています。旧 SDK (`azure-ai-formrecognizer`) とは API が異なるため混在させないでください。

### スキャン PDF デモ (任意)

`demo-factory-scanned.pdf` (画像化された PDF、OCR テスト用) を生成するには、追加で **pdf2image** と **poppler-utils** が必要です。スキャンデモが不要なら、この節はスキップしてください（`generate_demo_pdfs.py` は poppler が無ければ警告を出しつつ他の 2 PDF は生成します）。

```bash
# ライブラリ
pip install "pdf2image>=1.17.0"

# OS ネイティブの poppler
# Ubuntu / WSL2:
sudo apt-get install -y poppler-utils
# macOS (Homebrew):
brew install poppler
# Cloud Shell: 既にインストール済み
```

## 権限の確認

Bicep が Role Assignment を作成するため、以下のいずれかが必要です：

- **Owner** (推奨)
- **Contributor + User Access Administrator**

```bash
az role assignment list --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --subscription "$(az account show --query id -o tsv)" \
  --query "[].roleDefinitionName" -o tsv
```

次: [`02-provision.md`](02-provision.md)
