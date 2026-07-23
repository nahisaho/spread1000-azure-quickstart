# 01. 前提条件

## Materials Project アカウント

1. https://next-gen.materialsproject.org/ にアクセスし、無料アカウントを作成
2. ダッシュボード (`/dashboard`) から **API キーを取得**
3. 環境変数に設定:

   ```bash
   export MP_API_KEY=<your-32-char-key>
   ```

> [!IMPORTANT]
> 旧レガシー API (`materialsproject.org/rest`) のキーは新 API では使えません。**新 API 用のキー** (`next-gen.materialsproject.org` で取得) を使ってください。旧レガシー API は 2025 年 9 月に終了しています。

## ローカル環境 (推奨経路)

- **Python 3.12** を推奨 (matminer は 3.13 の公式 classifier を持ちません)
- Git、curl、bash
- WSL2 (Windows) または macOS / Linux
- ディスク空き 200 MB 以上

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

主要依存パッケージ:

| パッケージ | バージョン | 用途 |
|---|---|---|
| mp-api | >=0.46.4 | Materials Project API v2 クライアント |
| pymatgen | >=2026.5.4 | 結晶構造データ操作 |
| matminer | >=0.10.1 | 特徴量化 (Magpie 記述子) |
| xgboost-cpu | >=3.3.0 | 勾配ブースティング (CPU 版) |
| scikit-learn | >=1.9.0 | ベースライン + CV |
| pyarrow | >=20 | Parquet 入出力 |

> [!NOTE]
> **GPU は不要**です。データ量が数千件程度ならすべて CPU で完結します。`xgboost-cpu` は GPU ランタイムを含まない軽量パッケージです。

## Azure 側 (任意)

Azure ML Compute Instance で実行する場合のみ:

- Azure サブスクリプション
- 対象リソースグループへの `Contributor` + `User Access Administrator` (または `Owner`) 権限
- Standard_E2s_v3 (2 vCPU) のクォータ 2 以上、Japan East

```bash
az login
az account show --query name -o tsv
az ml compute list-usage --workspace-name <ws> --resource-group <rg> -o table
```

Bicep テンプレートは同梱していません。本教材はローカル / WSL2 / Cloud Shell で完結する CPU-only ワークフローのため、Azure リソースの払い出しが不要です。AML 上で実行したい場合は生命科学 01 の `infra/main.bicep` を参考にしてください。

## Cloud Shell を使う場合

- Python 3.12 が既にインストール済み
- 20 分無操作でタイムアウトするため、長い CV には不向き
- Materials Project からのデータ取得と学習だけなら十分間に合います
