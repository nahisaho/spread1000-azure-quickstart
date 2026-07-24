# 04. 生成ジョブの実行と評価

## 1. Environment の登録 (初回のみ)

```bash
az ml environment create -f aml/environment.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

初回は ACR で image build が 5〜10 分かかります。

## 2. Compute cluster の作成 (初回のみ)

```bash
az ml compute create -f aml/compute-cpu.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME"
```

`Standard_D4as_v5`, `min_instances=0`, `max_instances=1`, idle 120 秒でスケールダウン。

## 3. 生成 & スコアリングジョブ送信

```bash
az ml job create -f aml/job-generate.yml \
  -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" --web
```

`--web` で Studio のジョブ画面がブラウザで開きます。

**内部で実行される内容**:

1. `src/run_libinvent.py` — REINVENT4 LibInvent サンプリング (100 SMILES)
2. `src/score_molecules.py` — RDKit で MW/LogP/QED/TPSA/Validity/Uniqueness を計算し MLflow に log
3. `src/render_topk.py` — QED でソートした top-20 分子を PNG に描画

## 4. 結果の確認

**AML Studio 上**:

- **Metrics** タブ: `valid_ratio`, `unique_ratio`, `mean_qed`, `mean_mw`, `mean_logp`
- **Outputs + logs** タブ:
  - `outputs/user_logs/std_log.txt` — 実行ログ全文
  - job outputs → `molecules` (named output) → `sampled.csv` (raw REINVENT 出力), `scored.csv` (RDKit スコア付き), `top20.png` (QED top-20)

**CLI で確認**:

```bash
# 最新ジョブ ID を取得
JOB_NAME=$(az ml job list -g "$AZURE_RESOURCE_GROUP" -w "$AZURE_WORKSPACE_NAME" \
  --query "[?display_name=='reinvent4-libinvent-sampling'] | [0].name" -o tsv)

# 結果検証
python scripts/verify-output.py "$JOB_NAME"

# outputs をローカルにダウンロード
az ml job download \
  --name "$JOB_NAME" \
  -g "$AZURE_RESOURCE_GROUP" \
  -w "$AZURE_WORKSPACE_NAME" \
  --output-name molecules \
  --download-path ./molgen-outputs
```

## 5. 期待される数値（参考）

REINVENT4 v4.8 LibInvent 100 SMILES サンプリング（デフォルト scaffold `Cc1ccc([*:1])cc1[*:2]`）:

| 指標 | 目安 |
|---|---|
| Valid ratio | > 0.90 |
| Unique ratio | > 0.85 |
| Mean QED | 0.4〜0.6 |

数値は seed / scaffold / sample サイズに依存します。既定の `--seed 42` (job-generate.yml で指定) では同じスカフォールドを再実行すると同じサンプル群になります。異なる分子集合を得たい場合は seed を変更してください。

## 6. 自分の scaffold で試す

`aml/job-generate.yml` の `command:` セクション内 `--scaffold` パラメータを編集してから、`az ml job create` を再実行します:

```yaml
command: >-
  python run_libinvent.py
    --prior ${{inputs.priors}}/libinvent.prior
    --scaffold "Nc1ccc([*:1])cc1[*:2]"   # ← 自分の scaffold に置き換え
    --num-smiles 200
    --seed 42
    --output ${{outputs.molecules}}/sampled.csv &&
  ...
```

- attachment point は必ず `[*:1]`, `[*:2]` のように **番号付き**で記述
- LibInvent scaffold decoration は本チュートリアルでは **2 attachment point (`[*:1]` + `[*:2]`) を検証済み**。REINVENT4 LibInvent prior が受理する attachment 数の上限を超える場合は、`reinvent` CLI が exit code!=0 で失敗し `reinvent.log` にエラーが記録されます。多重リンカー (2 warhead を linker で結合) が目的の場合は LibInvent ではなく **LinkInvent** (別 prior、別ワークフロー) を使用してください — LinkInvent は「多点 decoration」の上位互換ではないことに注意
- サンプル数は `--num-smiles 200` のように大きくしても CPU で数分
