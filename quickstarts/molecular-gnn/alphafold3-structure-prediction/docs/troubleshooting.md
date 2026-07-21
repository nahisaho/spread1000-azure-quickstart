# トラブルシューティング

## デプロイ関連

### エラー: `The requested VM size is not available` / `SkuNotAvailable`

**原因**: 選んだリージョンで H100 (`Standard_NC40ads_H100_v5`) が枯渇しています。

**対処 (順に試す)**:
1. A100 80GB (`Standard_NC24ads_A100_v4`) にダウングレード
2. リージョン変更: `LOCATION=eastus2` または `westeurope`（データ所在ポリシーを確認）
3. 数時間〜数日待って再試行

利用可能な Azure ML GPU SKU を確認:

```bash
SUB_ID=$(az account show --query id -o tsv)
LOC=japaneast
az rest --method get \
  --url "https://management.azure.com/subscriptions/${SUB_ID}/providers/Microsoft.MachineLearningServices/locations/${LOC}/vmSizes?api-version=2024-04-01" \
  --query "value[?gpus > \`0\` && (contains(name, 'H100') || contains(name, 'A100'))].{Name:name, GPUs:gpus, vCPU:vCPUs, RAM_GB:memoryGB}" \
  -o table
```

capacity 事前確認:

```bash
az vm list-skus --location "${LOC}" --resource-type virtualMachines \
  --query "[?name=='Standard_NC40ads_H100_v5' || name=='Standard_NC24ads_A100_v4'].{Name:name, Restrictions:restrictions[].reasonCode}" \
  -o table
```

`Restrictions` が空でなければそのリージョンでは利用不可。

### エラー: `assignedUser is required`（Bicep デプロイ時）

**原因**: Bicep で Compute Instance を作るには「担当ユーザー」を明示指定する必要があります。

**対処**: `deploy.sh` は自動取得しますが、CI/CD 環境等で失敗する場合は明示指定:

```bash
MY_OID=$(az ad signed-in-user show --query id -o tsv)
MY_TID=$(az account show --query tenantId -o tsv)
```

## セットアップ関連

### エラー: `docker: Cannot connect to the Docker daemon`

**原因**: Compute Instance の Docker daemon が起動していない、または権限不足。

**対処**:

```bash
sudo systemctl status docker
sudo systemctl start docker
# 権限追加（再ログイン必要）
sudo usermod -aG docker $USER
```

`setup-af3.sh` は `sudo` 前提で書かれています。

### エラー: `docker: could not select device driver "" with capabilities: [[gpu]]`

**原因**: NVIDIA Container Toolkit が未インストール、または設定漏れ。

**対処**:

```bash
# 確認
nvidia-container-runtime --version
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi

# 未導入なら
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Azure ML Compute Instance の DSVM ベースイメージにはプレインストール済みです。

### エラー: Docker ビルドが `pip install jax==0.9.1` でハング / タイムアウト

**原因**: JAX の CUDA wheels は大容量（数 GB）で、ネットワークが不安定だと失敗します。

**対処**:

```bash
cd ~/alphafold3
# BuildKit 有効でリトライ、キャッシュ活用
DOCKER_BUILDKIT=1 docker build --progress=plain -t alphafold3:v3.0.2 -f docker/Dockerfile .
```

または PyPI のミラーを指定（社内ミラーがある場合）。

### `fetch_databases.sh` が途中で失敗する

**原因**: 単一 URL のダウンロードエラー、または `/mnt` 容量不足。

**対処**:

```bash
# 容量確認
df -h /mnt

# 部分ダウンロード済みのファイルを削除して再実行
du -sh /mnt/af3/public_databases/*
# 未完了ファイル (`.zst` / `.tar` のまま) を削除して再試行
sudo ./fetch_databases.sh /mnt/af3/public_databases
```

**注意**: `fetch_databases.sh` は robust resume を保証しません。中断時は該当ディレクトリを空にしてやり直す方が安全です。

### `af3.bin` の SHA-256 が承認メールと一致しない

**原因**: 転送中の破損、または重み配布パッケージのバージョン違い。

**対処**:

```bash
# 破損ならローカルで再ダウンロード後、再アップロード
sha256sum /mnt/af3/models/af3.bin

# Google の approval メールに記載された SHA-256 と一致することを確認
```

サイズ (約 1 GB) が明らかに違う場合は転送エラー。JupyterLab のアップロード機能は
大容量転送で不安定になることがあるので、`azcopy` または分割 SCP を検討。

## 推論関連

### エラー: `CUDA out of memory` / `OOM`

**原因**: 入力のトークン数がその GPU の限界を超えている。

**対処**:

| GPU VRAM | ~5,120 トークン | 更に大きい入力 |
|----------|----------------|--------------|
| H100 94 GB | ✅ 標準サポート | `--flash_attention_implementation=xla` + unified memory |
| A100 80 GB | ✅ 標準サポート | 上と同様 |
| A100 40 GB | 一部要工夫 | `pair_transition_shard_spec` 変更 + unified memory |

Docker 実行時に unified memory を有効化 (DeepMind の performance.md 記載の環境変数):

```bash
# 環境変数を追加
docker run --gpus all \
  -e XLA_PYTHON_CLIENT_PREALLOCATE=false \
  -e TF_FORCE_UNIFIED_MEMORY=true \
  -e XLA_CLIENT_MEM_FRACTION=3.2 \
  ...
```

`run-inference.py` は `--unified-memory` オプションで自動設定できます。

### エラー: `Ranking score < -99` / `has_clash=True`

**原因**: 深刻なステリック衝突が予測で発生。V100 世代 GPU (CUDA 8.0) では XLA バグで頻発します。

**対処**:

- H100/A100/L40S/RTX 4090 では通常発生しない
- V100 系を使うなら `XLA_FLAGS=--xla_disable_hlo_passes=custom-kernel-fusion-rewriter` を設定
- H100 で発生する場合は入力を再検証（不正な bondedAtomPairs、非常識な SMILES など）

### エラー: MSA/データパイプラインが遅すぎる（数時間かかる）

**原因**: DB が遅いストレージ (Azure Files 標準, BlobFuse) に置かれている。

**対処**:

- **必ず `/mnt` ローカル NVMe を使う**（`Standard_NC40ads_H100_v5` は 3.5 TiB NVMe）
- `df -h /mnt/af3/public_databases` で NVMe に置かれていることを確認
- Azure Files に永続化している場合は起動時に `/mnt` にコピーする運用を推奨

### 初回推論が非常に遅い（10 分以上）

**原因**: JAX の JIT コンパイル（初回のみ）。

**対処**: `--jax-cache-dir ~/cloudfiles/jax-cache` を必ず指定。2 回目以降はキャッシュから数秒で復元。

キャッシュを永続領域に置かないと Compute Instance を停止するたびに再コンパイルが発生します。

### エラー: 不正な JSON / スキーマエラー

**原因**: `dialect`, `version`, `sequences` のいずれかが規約と異なる。

**対処**: 以下を必須:

```json
{
  "name": "...",
  "sequences": [...],
  "modelSeeds": [42],
  "dialect": "alphafold3",
  "version": 4
}
```

- `dialect` は `"alphafold3"` （AlphaFold Server 形式 (トップレベル配列) は AF3 v3.0.2 が自動変換するため、そのまま `--json_path` に渡せます。ただし省略された `modelSeeds` はランダム生成され、`dialect`/`version` は `alphafoldserver`/`1` として扱われるため、**再現性を保つ場合は明示的に `modelSeeds` を設定**してください）
- `version` は 4（新規入力）
- `modelSeeds` は空でなく少なくとも 1 つの整数

## Compute Instance 停止・保存関連

### `/mnt` の DB が消えた

**原因**: Compute Instance を停止 (deallocate) した。`/mnt` は一時 NVMe。

**対処**: `setup-af3.sh` を再実行し、DB を再ダウンロード（60〜120 分）。頻繁に停止する場合は
[`docs/05-cleanup.md`](05-cleanup.md) の「DB の永続化」を参照。

### 自動停止（idle shutdown）が働かない

**原因**: Bicep API 2024-04-01 では `idleTimeBeforeShutdown` が正式スキーマ外で、サーバー側では受理されるが反映されないケースがあります。また、Workspace のマネージド ID にロール割当がないと反映されていても停止が実行されません（[`docs/02-provision-aml.md`](02-provision-aml.md) の重要事項を参照）。

**対処**: Azure ML Studio → **コンピューティング** → 該当 CI 選択 → **アクション** → **アイドル シャットダウンの編集** で 60 分を設定。

**H100 は時給 ¥1,637 なので、停止忘れは 1 日で ¥39,000 の課金**です。手動停止を習慣化してください。

## ライセンス関連

### 「af3.bin を同僚と共有していいですか？」

**原則ダメ**です。次の判定を行ってください:

1. あなたの承認は **個人** か **機関代表者** か？
   - Google フォーム申請時、authorized institutional representative を選択したかを確認
2. 個人承認なら **同僚と共有不可**（`~/cloudfiles/` に置くのも避ける）
3. 機関代表者承認なら、承認された組織の従業員/協力者と共有可（承認要件の範囲内）

判定に迷ったら所属機関の法務またはコンプライアンス窓口に相談してください。

### 「AF3 の出力を論文に載せていいですか？」

学術論文への掲載は **可** ですが、以下を満たす必要があります:

1. **AF3 Nature 論文を引用** — <https://www.nature.com/articles/s41586-024-07487-w>
2. **出力ディレクトリの `TERMS_OF_USE.md` を保持**（修正可、ただし帰属明示）
3. 商用パートナーに独占ライセンスを渡さない（非商用条件を破らない）

## ネットワーク / 認証関連

### Jupyter に接続できない（Compute Instance の URL がタイムアウト）

**原因の可能性**:
1. Compute Instance の `state` が `Stopped` → `az ml compute start` で起動
2. VNet 統合 Workspace を使っており、社内 Proxy が Jupyter へのアクセスを遮断
3. `assignedUser` が自分ではない（サービスプリンシパルが所有）

**対処**:
```bash
az ml compute show --name ci-af3-$(whoami) \
  --resource-group <RG> \
  --workspace-name <WS> \
  --query "{state:state, assignedUser:personalComputeInstanceSettings.assignedUser.objectId}"
```

`assignedUser.objectId` が自分の Object ID (`az ad signed-in-user show --query id -o tsv`) と一致しない場合は、CI を削除して deploy.sh を再実行してください。
