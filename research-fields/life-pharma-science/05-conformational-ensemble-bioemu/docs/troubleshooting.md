# Troubleshooting — BioEmu on Azure ML

## 目次

- [Environment ビルドが失敗する](#environment-ビルドが失敗する)
- [Job が Queued のまま進まない](#job-が-queued-のまま進まない)
- [`bioemu.sample` が OOM で落ちる](#bioemusample-が-oom-で落ちる)
- [`num_samples` より少ない frame しか出ない](#num_samples-より少ない-frame-しか出ない)
- [AlphaFold params のオフライン化](#alphafold-params-のオフライン化)
- [MSA サービス (ColabFold) がタイムアウトする](#msa-サービス-colabfold-がタイムアウトする)
- [JAX がメモリを食い尽くす](#jax-がメモリを食い尽くす)
- [Spot ノードが中断される](#spot-ノードが中断される)
- [結果に NaN や壊れた構造が混ざる](#結果に-nan-や壊れた構造が混ざる)
- [リソース削除が失敗する](#リソース削除が失敗する)

---

## Environment ビルドが失敗する

**症状**: `az ml environment create` の直後、AML Studio → Environments で **Build failed**。

**確認**: Studio → Environments → `bioemu-1-4-1-cuda` → Build logs でエラーメッセージ全文を取得。

**よくある原因**:

1. **Python 3.11 の追加インストールで apt が失敗** — `deadsnakes` PPA がミラー障害。base image を、その時点で公開されている**新しい immutable tag** (例: `mcr.microsoft.com/v2/azureml/openmpi5.0-cuda12.4-ubuntu22.04/tags/list` で最新を確認) に差し替えて再試行:
   ```dockerfile
   FROM mcr.microsoft.com/azureml/openmpi5.0-cuda12.4-ubuntu22.04:<新しい immutable tag>
   ```
   `:latest` は再現性を壊すので、必ず日付付きの immutable tag を使う。

2. **pip が JAX cuda12 wheel を解決できない** — nvidia-cuda-nvcc-cu12 のバージョン不整合。以下を試す:
   ```dockerfile
   RUN python3 -m pip install --upgrade pip==24.3 \
    && python3 -m pip install "bioemu[cuda]==1.4.1" \
         --extra-index-url https://pypi.nvidia.com
   ```

3. **build に 45 分以上かかりタイムアウト** — AML environment build は最大 60 分。base image を直接 ACR に push し、`build:` を使わず `image:` で参照する方式に切り替える (`environment.yml` を書き換え):
   ```yaml
   image: <your-acr>.azurecr.io/bioemu:1.4.1
   ```

## Job が Queued のまま進まない

**症状**: `az ml job show --query status` が 10 分以上 `Queued`。

**確認**:

```bash
az ml compute show --name gpu-a100 -o jsonc
```

- `state: "Failed"` → compute 再作成
- `errors:` に quota エラー → [01. 前提条件 §GPU クォータ](01-prerequisites.md#gpu-クォータ) 参照
- `tier: "low_priority"` かつ Japan East が Spot 需要ピーク → `tier: dedicated` に一時変更

Spot 供給不足を CLI で確認:

```bash
az vm list-skus --location japaneast \
  --size Standard_NC24ads_A100_v4 \
  --query "[].{name:name, restrictions:restrictions}" -o jsonc
```

`restrictions` に `NotAvailableForSubscription` が含まれる場合は一時的な枯渇。数十分〜数時間待つか、`westus2` などのリージョンに切り替えて再デプロイ。

## `bioemu.sample` が OOM で落ちる

**症状**: `torch.cuda.OutOfMemoryError` または `XlaRuntimeError: RESOURCE_EXHAUSTED`.

**原因**: pair embedding が L×L のため、長い配列で急激に VRAM を消費。BioEmu は **自動リトライしません**。

**対処 (優先順)**:

1. **JAX の preallocate を切る** (デフォルトで環境変数を設定済みだが再確認):
   ```yaml
   # bioemu-sample.yml の command 先頭
   command: >-
     export XLA_PYTHON_CLIENT_PREALLOCATE=false;
     ...
   ```

2. **`batch_size_100` を下げる**:
   ```yaml
   command: >-
     ...
     python -m bioemu.sample
     --sequence ${{inputs.sequence}}
     --num_samples ${{inputs.num_samples}}
     --batch_size_100 2   # デフォルト 10
     --output_dir ${{outputs.ensemble}}
     ...
   ```
   長い配列 (>300 残基) はすでに内部で 1 にクリップされるため効果は限定的。

3. **より大きな GPU に切り替え**: `Standard_NC40ads_H100_v5` (94 GB) の compute を作り直す。ただし PAYG ¥1,500/h と高価。

4. **配列を分割**: 明確なドメイン境界があれば、各ドメインを独立 Job で処理し、結果を組み合わせる (BioEmu は multimer 非対応のため注意)。

## `num_samples` より少ない frame しか出ない

**症状**: `num_samples: 100` を指定したのに `samples.xtc` が 60 frame しかない。

**原因**: `filter_samples=True` (default) により、chain break や steric clash を含む構造が除外される。**これは正常動作**で、物理的により妥当な frame のみ残ることを意味します。

**対処**:

- **そのまま解析**: 60 frame でも十分な統計が取れることが多い
- **多めに生成**: `num_samples: 200` にして目標 100 frame を狙う
- **全 frame を保持** (デバッグ用):
   ```yaml
   command: >-
     ...
     python -m bioemu.sample
     ...
     --filter_samples=False
   ```
   ただし出力に非物理的構造が混ざることを許容する場合のみ。

## AlphaFold params のオフライン化

**症状**: 毎 Job で 3.5 GB を再ダウンロードしている。または managed VNet で GCS 到達不可。

**対処**: パラメータを workspaceblobstore に staging し、Job 内で mount:

**Step 1**: ローカルにダウンロード:

```bash
curl -L https://storage.googleapis.com/alphafold/alphafold_params_2021-07-14.tar \
  -o alphafold_params.tar
mkdir -p alphafold-params/params
tar -xf alphafold_params.tar -C alphafold-params/params
```

**Step 2**: workspaceblobstore にアップロード:

```bash
CONTAINER=$(az ml datastore show --name workspaceblobstore --query container_name -o tsv)

az storage blob upload-batch \
  --account-name "$AZURE_STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination "$CONTAINER" \
  --destination-path "cache/colabfold" \
  --source alphafold-params \
  --overwrite
```

**Step 3**: Job YAML に mount を追加:

```yaml
inputs:
  ...
  alphafold_cache:
    type: uri_folder
    path: azureml://datastores/workspaceblobstore/paths/cache/colabfold/
    mode: ro_mount

command: >-
  set -eux;
  export HOME=$(pwd);
  mkdir -p "$HOME/.cache/colabfold/params";
  cp -r ${{inputs.alphafold_cache}}/params/* "$HOME/.cache/colabfold/params/";
  # ColabFold は params ディレクトリ内の marker file を見て「DL 完了」と判定する。
  # ファイル無し → 再ダウンロードを試みるので、必ず作る。
  touch "$HOME/.cache/colabfold/params/download_finished.txt";
  export XLA_PYTHON_CLIENT_PREALLOCATE=false;
  python -m bioemu.sample ...
```

これで 2 回目以降の Job は 3.5 GB ダウンロードをスキップします。

> [!IMPORTANT]
> `download_finished.txt` を作り忘れると、offline VNet / 従量課金対策の意味が失われます。ColabFold は「params ディレクトリはあるが完了マーカーが無い」場合、既存ファイルを破棄して GCS から再取得しようとします。managed VNet で GCS 到達不可なら FailedNetworkError で Job が落ちます。

## MSA サービス (ColabFold) がタイムアウトする

**症状**: `HTTPSConnectionPool(host='api.colabfold.com', ...): Read timed out`.

**原因**: ColabFold の公共 MMseqs2 サービスは無料でレート制限あり。長い配列で遅い / 混雑時にタイムアウト。

**対処**:

1. **既存の A3M ファイルを渡す**: BioEmu は FASTA の代わりに **A3M** (query が 1 行目) を受け付ける:
   ```bash
   # 手元で ColabFold を回して A3M を作成
   colabfold_batch input.fasta result/ --msa-only
   # result/*_env/*.a3m を BioEmu に渡す
   ```
   Job YAML の inputs で `path: ./inputs/target.a3m` を指定。

2. **`--msa_host_url` を切り替え**: 自前 MMseqs2 API を持っていれば、`--msa_host_url https://your-host/`。

## JAX がメモリを食い尽くす

**症状**: `Job が start 直後に落ちる` `Out of memory: cudaMalloc`.

**原因**: JAX はデフォルトで GPU メモリの 90% を preallocate する。BioEmu の PyTorch モデルと競合。

**対処**: Job command 先頭で必ず設定:

```bash
export XLA_PYTHON_CLIENT_PREALLOCATE=false
```

(Dockerfile と bioemu-sample.yml の両方で設定済みだが、独自 command を書く場合は忘れずに)

## Spot ノードが中断される

**症状**: `Job status: Failed`, message に `low priority` / `preempted` を含む。

**対処**:

- **短い Job なら再投入**: chignolin (~20 分) の Spot 中断率は Japan East で数%程度
- **PAYG に切り替え**: `aml/compute-a100.yml` の `tier: low_priority` → `tier: dedicated`
- **BioEmu の checkpointing**: BioEmu は **run-level の resume を持たない** (各 batch は独立完了)。中断された batch は失われるので、run を分割して独立 seed で並列投入するのが実務的:
  ```bash
  for SEED in 1 2 3 4; do
    az ml job create --file aml/bioemu-sample.yml \
      --set inputs.seed=$((20260807 + SEED * 1000)) \
      --set inputs.num_samples=25 \
      --set display_name=bioemu-chignolin-seed$SEED
  done
  ```

## 結果に NaN や壊れた構造が混ざる

**症状**: `verify-output.py` が `❌ NaN/inf が座標に含まれる` を出力。

**原因**:

1. Numerical instability (稀。JAX + fp16 混在時)
2. Post-filter を無効化した状態で異常構造が残った

**対処**:

- `--filter_samples=True` (default) を確認
- BioEmu のバージョンを最新に固定 (1.4.1 で修正されたバグの可能性): `bioemu[cuda]==1.4.1`
- 再現するなら [microsoft/bioemu Issues](https://github.com/microsoft/bioemu/issues) で報告

## リソース削除が失敗する

**症状**: `az group delete` が 30 分以上かかる、または失敗。

**原因の候補**:

1. **Managed identity の孤立 role assignment** — サブスクリプションスコープを確認:
   ```bash
   az role assignment list --all --assignee <workspace-mi-principal-id> -o table
   az role assignment delete --ids <assignment-id>
   ```

2. **Storage の legal hold / immutability policy**:
   ```bash
   az storage container immutability-policy show \
     --account-name "$AZURE_STORAGE_ACCOUNT" --container-name workspaceblobstore
   az storage container legal-hold clear ...
   ```

3. **Key Vault soft-delete** (7 日残る):
   ```bash
   az keyvault list-deleted --query "[].name" -o tsv
   az keyvault purge --name <kv-name>
   ```

4. **Private endpoint / private DNS zone** が別 RG にある — Portal → 該当 RG → Private endpoint を先に削除。

すべて手動で消えない場合は Support Ticket が最終手段。
