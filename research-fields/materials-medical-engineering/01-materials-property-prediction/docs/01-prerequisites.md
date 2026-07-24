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
- WSL2 (Windows) / Linux / macOS のいずれか
- ディスク空き **1〜2 GB 以上** (SciPy / PyArrow / matplotlib / pymatgen / matminer データ + `pip cache` 込み)

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
| xgboost-cpu (Linux/Windows) / xgboost (macOS) | >=3.3.0 | 勾配ブースティング |
| scikit-learn | >=1.9.0 | ベースライン + CV |
| pyarrow | >=20 | Parquet 入出力 |

> [!NOTE]
> **GPU は不要**です。数千件程度なら CPU で完結します。`xgboost-cpu` は Linux/Windows のみ公式 wheel が提供されており、macOS では PyPI に該当パッケージが存在しないため `requirements.txt` は `platform_system` マーカーで通常版 `xgboost` を選択します。

> [!WARNING]
> **Cloud Shell はサポート対象外**です。Microsoft Learn の現行ドキュメントでは Cloud Shell 標準の Python は 3.9 系で、本教材が要求する 3.12 系ではありません (`xgboost-cpu>=3.3` は Python 3.12+ 必須)。Cloud Shell は `az` CLI ターミナルとしてのみ使ってください。

## Azure 側 (任意 — 本教材の主経路ではありません)

本教材はローカルで完結する CPU-only ワークフローのため、**Bicep / infra / deploy スクリプトは同梱していません**。既に Azure ML ワークスペースを持っていて再現環境として使いたい場合のみ、以下の**最小権限ロール**で AML Compute Instance を起動できます:

- サブスクリプション: ワークスペース所有済み
- ワークスペーススコープの `AzureML Data Scientist` + `AzureML Compute Operator` (ロール割り当ての権限は不要)
- Standard_E2s_v3 (2 vCPU) のクォータ 2 以上、Japan East
- **idle shutdown を必ず設定** (Compute Instance の作成時 `--idle-time-before-shutdown 30`)

クォータ確認 (現行 CLI は `--resource-group` が必須):

```bash
az extension add -n ml --upgrade
az ml compute list-usage --resource-group <rg> --workspace-name <ws> -o table
```

> [!IMPORTANT]
> `Owner` / `User Access Administrator` は不要です (ロール割り当ての権限は本教材で使いません)。既に発行済みのワークスペースに `Data Scientist` として招待してもらう運用を推奨します。

## 追加チェック
