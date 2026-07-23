# 06 — 後片付け

## ローカル環境

```bash
# 生成データ + 学習済み重みを削除
rm -rf data/*.png data/samples data/predictions data/checkpoints data/*.json

# 仮想環境ごと削除
deactivate
rm -rf .venv
```

## Azure ML Compute Instance

### ⚠️ 停止するのを忘れないでください

**Compute Instance は起動しているだけで課金されます** (PAYG $0.71/hr、1 日で $17)。

### 停止 (再利用予定)

Studio → 「Compute」→ 該当インスタンス → 「Stop」

CLI:
```bash
az ml compute stop --name <ci-name> --workspace-name <ws-name> \
  --resource-group <rg-name>
```

停止中はコンピュート課金 0 ですが、OS ディスク (128 GB Std SSD) は月 ~$7 続きます。

### 削除 (完全に不要)

Studio → 「Compute」→ 該当インスタンス → 「Delete」

CLI:
```bash
az ml compute delete --name <ci-name> --workspace-name <ws-name> \
  --resource-group <rg-name> --yes
```

### GPU Cluster (CommandJob 用)

```bash
az ml compute delete --name gpu-cluster-nc4t4 \
  --workspace-name <ws-name> --resource-group <rg-name> --yes
```

### Azure ML ワークスペース全体削除

もう Azure ML 自体を使わない場合:
```bash
az group delete --name <rg-name> --yes --no-wait
```

## コスト確認

Azure Portal → 「コスト管理」→ 「コスト分析」で当月請求額を確認。**予算アラート ($10 など)** を設定しておくと安心:
```
Portal → サブスクリプション → 予算 → + 追加
```

## チェックリスト

- [ ] `data/` 以下の生成物 (PNG/JSON/PTH) を削除
- [ ] Azure を使った場合、Compute Instance を Stop / Delete
- [ ] CommandJob を使った場合、GPU Cluster を Delete
- [ ] Azure ML 全体不要ならリソースグループを削除
- [ ] Azure Portal のコスト分析で請求額確認
