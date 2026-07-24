# 06 — 片付けと次のステップ

## ローカルで完結した場合

Azure リソースは一切作成していないので、**追加の料金は発生しません**。

不要になれば以下を削除して構いません:

```bash
rm -rf data/ outputs/ .venv/
```

- `data/train/`, `data/val/`, `data/test/`, `data/samples/`: `generate_data.py` の再実行で再生成
- `outputs/`: 学習成果物。別途保存したい場合は先に別ディレクトリへ退避

## Azure ML を使った場合

> [!WARNING]
> **ゼロへのスケールダウン ≠ 完全無料**
>
> `min-instances=0` のコンピュートクラスターは VM ノード費用が 0 になりますが、
> **以下の費用は継続して発生します**:
> - AML ワークスペースのデフォルトストレージ (ジョブ出力・ログが残る)
> - Log Analytics ワークスペースのデータ保持
>
> 完全にコスト 0 にするには RG ごと削除してください (下記参照)。

> [!NOTE]
> **停止済み Compute Instance の費用**
> Compute Instance を停止 (stop) してもゼロにはなりません。
> OS ディスク (P10: 約 $1.54/月) + Standard Load Balancer の費用が残ります。
> 不要な場合は削除してください。

### .env を読み込む

cleanup コマンドはすべて `.env` の値を使います:

```bash
source .env
# → AML_SUBSCRIPTION_ID, AML_RESOURCE_GROUP, AML_WORKSPACE_NAME,
#    AML_KEY_VAULT_NAME, AML_LOCATION が設定される
```

### Compute cluster の削除

```bash
az ml compute delete \
  --name gpu-t4 \
  -g "$AML_RESOURCE_GROUP" \
  -w "$AML_WORKSPACE_NAME" \
  --yes
```

### Compute Instance の削除 (作成した場合)

```bash
az ml compute delete \
  --name <インスタンス名> \
  -g "$AML_RESOURCE_GROUP" \
  -w "$AML_WORKSPACE_NAME" \
  --yes
```

### インフラ全体の削除

> [!DANGER]
> **このシナリオの deploy.sh で作成した専用 RG のみ削除してください。**
> 既存のワークスペース / リソースグループを流用した場合は `az group delete` を
> **実行しないでください** — 無関係なリソースが全削除されます。

```bash
# Bicep で作成したデプロイを削除 (任意; RG 削除で代替可)
az deployment group delete \
  --name main \
  -g "$AML_RESOURCE_GROUP"

# リソースグループごと削除 (このシナリオ専用 RG の場合のみ)
az group delete \
  -n "$AML_RESOURCE_GROUP" \
  --subscription "$AML_SUBSCRIPTION_ID" \
  --yes --no-wait
```

### Key Vault のパージ (soft-delete 後の完全削除)

soft-delete が有効な KV は削除後も保持期間中は残ります。完全に消すには:

```bash
# 名前を厳密に .env から取得 (手動タイプ不要)
KV_NAME=$(az keyvault list-deleted \
  --query "[?name=='${AML_KEY_VAULT_NAME}'].name | [0]" \
  -o tsv 2>/dev/null || echo "")

if [[ -n "$KV_NAME" ]]; then
  az keyvault purge --name "$KV_NAME" --location "$AML_LOCATION"
  echo "Purged: $KV_NAME"
else
  echo "Key Vault ${AML_KEY_VAULT_NAME} is not in deleted state or already purged."
fi
```

## 応用のヒント

### 別の劣化タイプに変える

`src/generate_data.py::add_gaussian_noise` を差し替えるだけで別の劣化タイプに拡張できます:

```python
def add_poisson_gaussian(img, alpha, sigma_read, rng):
    """ショットノイズ (Poisson) + 読み出しノイズ (Gaussian) の混合."""
    lam = np.clip(img, 0, 1) * alpha
    shot = rng.poisson(lam=lam) / alpha
    read = rng.normal(0, sigma_read, size=img.shape)
    return np.clip(shot + read, 0, 1).astype(np.float32)
```

### 実データに置き換える

`NoisyCleanDataset` は `.npz` の `clean` / `noisy` キーを読むだけです。実データを
`(1, H, W) float32 in [0, 1]` に前処理して同じ形式で保存すれば、そのまま学習できます。

**実データ移行時の注意**:

1. **正規化範囲**: 実 RAW は 12〜16 bit 整数。`float32 / (2**bits - 1)` で [0,1] に正規化
2. **サイズ**: MiniUNet は 4 の倍数の入力を要求
3. **チャネル数**: 3ch RGB なら `MiniUNet(in_channels=3, out_channels=3)`
4. **データ分割**: パッチ抽出時は同一ソース画像が train/val/test に混在しないよう
   `source_image_id` でグループ分割すること (generate_data.py のコメント参照)
5. **医療データ**: 患者/被験者 ID でグループ分割してリーク防止

### 大規模化

- **より深い U-Net**: `base=32` にすると ~470K params
- **注意 (attention U-Net)**: skip connection に attention gate を追加
- **拡散モデル**: DiT/Latent Diffusion で条件生成

## 次のステップ

- [01: Phi-4-mini LoRA ファインチューニング](../01-llm-lora/) — LLM 系
- [02: 時系列信号分類 (1D-CNN)](../02-timeseries-1dcnn/) — 生体信号系
- 他分野: [ルート README](../../../README.md)
