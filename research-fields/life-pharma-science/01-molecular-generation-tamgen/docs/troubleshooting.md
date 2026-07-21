# トラブルシューティング

よくある問題と解決策。頻度順に並べています。

---

## Compute Instance が作成できない

### エラー: `Quota exceeded` / `SubscriptionUsageQuotaExceeded`

**原因**: Azure ML の GPU クォータが 0 または不足しています（VM 全体のクォータとは別枠です）。

**対処**: [01-prerequisites.md #4](01-prerequisites.md#4-gpu-クォータ重要見落とし多発ポイント) の手順で **Portal から Machine Learning プロバイダーのクォータ** を増やしてください。承認まで 1〜2 営業日待ちます。

### エラー: `The requested VM size is not available` / `SkuNotAvailable`

**原因**: 選んだリージョンで指定 GPU SKU が枯渇しています（特に japaneast の A100 系）。

**対処**:
1. `Standard_NC8as_T4_v3`（T4 16GB）にダウングレード — 100M モデルの動作確認には十分
2. または `LOCATION` を `eastus2` / `swedencentral` に変更（deploy.sh または Bicep パラメータ）

利用可能な Azure ML GPU SKU を確認：

```bash
SUB_ID=$(az account show --query id -o tsv)
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/japaneast/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\`].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

> [!NOTE]
> **`Standard_NC6s_v3`（V100）は 2025-09-30 に japaneast を含む主要リージョンで廃止済み** です。旧手順で見かけても選ばないでください。

### エラー: `assignedUser is required`（Bicep デプロイ時）

**原因**: Bicep で Compute Instance を作るには「担当ユーザー」を明示指定する必要があります。

**対処**: `parameters.json` に以下を設定：

```bash
MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)

# parameters.json に "assignedUserObjectId": "$MY_OID", "assignedUserTenantId": "$MY_TID" を入れる
```

CI/CD からデプロイする場合は、実際に Jupyter を使う研究者のオブジェクト ID を渡してください。

---

## セットアップスクリプトが途中で止まる

### `setup_env.sh` が `conda install` の確認プロンプトで停止

**原因**: 上流の `setup_env.sh` は `conda install ... -y` を付けていません。

**対処**: 本クイックスタートの `setup-tamgen.sh` は `CONDA_ALWAYS_YES=true` を付けて呼び出しているので通常起きません。手動で上流スクリプトを叩いた場合は以下：

```bash
CONDA_ALWAYS_YES=true bash setup_env.sh
```

### `setup_env.sh` が `pip install` で失敗

**原因**: PyPI/conda-forge の一時的な接続不安定。

**対処**:
```bash
cd ~/TamGen
CONDA_ALWAYS_YES=true bash setup_env.sh   # 再実行するとキャッシュから継続
```

### Zenodo からのダウンロードが遅い / 失敗 / MD5 不一致

**原因**: Zenodo 側の混雑 or ネットワーク断による部分ダウンロード。

**対処**: `setup-tamgen.sh` は `curl --continue-at -` で再開に対応しています。何度か再実行してください。

```bash
bash ~/spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
```

それでも MD5 不一致が続く場合、`/tmp/*.zip` を手動削除してから再実行してください。

---

## `torch.cuda.is_available()` が False

**原因 1**: CPU 系 Compute を選んでいる。

**対処**: [02-provision-aml.md](02-provision-aml.md) をやり直し、**GPU** カテゴリの VM サイズを選択。

**原因 2**: 何らかの理由で CPU 版 PyTorch がインストールされた。

**対処**: **PyTorch 単体を差し替えないでください。** 上流の PyTorch 2.3.0 / CUDA 12.1 / torch_geometric 2.3.0+cu121 の組合せは ABI がタイトに結合しています。conda 環境を作り直すのが最も安全です：

```bash
conda deactivate
conda env remove -n TamGen -y
bash ~/spread1000-azure-quickstart/research-fields/life-pharma-science/01-molecular-generation-tamgen/scripts/setup-tamgen.sh
```

---

## `Python 3.9 (TamGen)` カーネルが Notebook で選べない

**対処**: `setup-tamgen.sh` の最後に自動登録されますが、手動でやり直したい場合：

```bash
conda activate TamGen
python -m ipykernel install --user --name tamgen --display-name "Python 3.9 (TamGen)"
```

Studio 側でノートブックを開き直すか、右上のカーネルアイコンでリスト再取得。

---

## Compute Instance のホームディレクトリが Studio に見えない

**原因**: Azure ML Studio の **ノートブック** タブは既定で `Users/<ユーザー>/` を見ています。`~/TamGen`（=`/home/azureuser/TamGen`）はここには表示されません。

**対処 (推奨)**: 必要なノートブックだけ Studio 可視領域にコピーする：

```bash
mkdir -p "${HOME}/cloudfiles/code/Users/$(whoami)/tamgen"
cp ~/TamGen/interctive_decode.ipynb \
   "${HOME}/cloudfiles/code/Users/$(whoami)/tamgen/interactive_decode.ipynb"
```

（上流ファイル名は "interctive"（誤字）です。Studio 内では読みやすい "interactive" で置き直しています。）

**対処 (非推奨・自前で Jupyter を起動)**: Compute Instance 上で直接 Jupyter を上げる場合、**必ず localhost にバインドし、SSH トンネル経由でアクセス** してください（`--ip=0.0.0.0` は全ネットワーク公開になり危険）：

```bash
conda activate TamGen
cd ~/TamGen
jupyter lab --ip=127.0.0.1 --port=8888 --no-browser
# 別ターミナルから: az ml compute connect-ssh (Studio の SSH 接続機能で確立) 経由でポートフォワード
```

Studio の統合 Jupyter を使うのが最も安全です。

---

## 生成分子が SMILES として無効

**原因**: TamGen は稀に化学的に無効な SMILES を出力します（1〜5% 程度）。本クイックスタートの `generate_from_pdb.py` は RDKit の `filter_generated_cmpd()`（上流実装）で自動フィルタしているため、`generated_molecules.csv` に載るのは既に妥当なもののみです。

**多様性が低い場合**: 上流 `TamGenDemo.__init__` の `--sample-beta` を大きくします（デフォルト 1.0、推奨レンジ 0.1〜2.0）。

---

## リソース削除できない (Key Vault が残る)

**原因**: Key Vault はソフト削除保護（7 日）が既定で有効。

**対処**: [05-cleanup.md](05-cleanup.md) の C 節に **安全なパージ手順**（RG から名前を取得 → 対話確認 → パージ）があります。**古いガイドで見かける「`kv-tamgen` を含む Vault をすべてパージ」は他ユーザーの Vault を破壊しかねないため使わないでください。**

---

## それでも解決しないとき

- [microsoft/TamGen Issues](https://github.com/microsoft/TamGen/issues) を検索・起票
- Azure ML のエラーは [Azure ML docs](https://learn.microsoft.com/ja-jp/azure/machine-learning/) と Portal の **診断ツール**
- 本リポジトリの [Issue](https://github.com/nahisaho/spread1000-azure-quickstart/issues) にご報告ください

