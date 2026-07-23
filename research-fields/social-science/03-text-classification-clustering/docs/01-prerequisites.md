# 01. 前提条件

## Azure 側

- Azure サブスクリプション (無料試用可)
- サブスクリプションに **Cognitive Services / Azure OpenAI** の割当と Japan East リージョンでのクォータ (1 アカウント、Embedding 30K TPM + GPT-5.4-mini 30K TPM)
- 対象リソースグループへの権限:
  - `Contributor` (リソース作成用) **に加えて**
  - `User Access Administrator` または `Owner` (Bicep 内のロール割当用。`Microsoft.Authorization/roleAssignments/write` 権限が必要)
- Azure CLI 2.65 以上 (`az version`)、Bicep CLI (`az bicep install`)

```bash
az login
az account set --subscription <sub-id>
az account show --query name -o tsv
```

## ローカル環境

- Python 3.11 以上 (3.13 推奨、scikit-learn 1.9 が対応)
- Git、curl、bash
- 開発用に VS Code + Python 拡張を推奨 (任意)

## Python 環境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` の主要依存:

| パッケージ | バージョン | 用途 |
|---|---|---|
| openai | >=2.47.0 | v1 API クライアント |
| azure-identity | >=1.25.3 | Managed Identity 認証 |
| scikit-learn | >=1.9.0 | 分類 / クラスタリング / silhouette |
| numpy / pandas | numpy>=2.0, pandas>=2.2 | ベクトル・表データ |
| pydantic | >=2.8 | Structured Outputs スキーマ |
| umap-learn | >=0.5.7 | 可視化 (2 次元投影) — [docs/05](docs/05-cluster.md) の追加サンプルで使用 |

> [!NOTE]
> **形態素解析ライブラリは必要ありません**。Embedding-3 は日本語の生テキストをそのまま処理します。SudachiPy / fugashi は必要になったら別途 `pip install` してください。

## クォータの事前確認

Japan East で使いたい Embedding-3 small の Regional Standard デプロイと GPT-5.4-mini GlobalStandard デプロイのクォータ (それぞれ 30K TPM 分) が確保できるか確認します。

```bash
az cognitiveservices usage list --location japaneast \
  --query "[?contains(name.value, 'OpenAI') || contains(name.value, 'Standard.text-embedding') || contains(name.value, 'gpt-5.4-mini')]" \
  -o table
```

不足している場合は Azure Portal から増枠申請してください。
