# 06 — 後片付け

## ローカル環境の場合

```bash
# 生成データを削除（venv とキャッシュは残す）
rm -rf data/*.traj data/*.extxyz data/*.cif data/*.log data/*.json

# MACE モデルキャッシュも消したい場合（次回再ダウンロード ~80 MB）
rm -rf ~/.cache/mace/

# 仮想環境ごと削除
deactivate
rm -rf .venv
```

## Azure ML Compute Instance の場合

### ⚠️ 最重要: 停止するのを忘れないでください

**Compute Instance は起動しているだけで課金されます。** セッション終了時に必ず停止 or 削除してください。

### 停止（あとで再利用する場合）

Azure ML Studio → 「Compute」→ 「Compute instances」→ 該当インスタンスを選択 → 「Stop」

停止中はコンピュートの課金は 0 になりますが、**OS ディスク（128 GB Std SSD）** の課金は継続します（月 ~$7）。

CLI から:
```bash
az ml compute stop --name <ci-name> --workspace-name <ws-name> \
  --resource-group <rg-name>
```

### 削除（完全に不要な場合）

Azure ML Studio → 「Compute」→ 該当インスタンスを選択 → 「Delete」

CLI から:
```bash
az ml compute delete --name <ci-name> --workspace-name <ws-name> \
  --resource-group <rg-name> --yes
```

### Azure ML ワークスペース全体の削除

もう Azure ML 自体を使わない場合、リソースグループごと削除するのが最も確実です:

```bash
az group delete --name <rg-name> --yes --no-wait
```

削除には 5〜15 分程度かかります。完了後、Azure Portal のリソースグループ一覧から消えていることを確認してください。

## コスト確認

Azure Portal → 「コスト管理」→ 「コスト分析」で当月の請求額を確認できます。**サブスクリプション予算アラート**を $10 などに設定しておくと、想定外の請求を早期発見できます:

```
Portal → サブスクリプション → 予算 → + 追加
```

## チェックリスト

- [ ] `data/*.traj`, `data/*.extxyz`, `data/*.cif` を削除した
- [ ] Azure を使った場合、Compute Instance を「Stop」または「Delete」した
- [ ] Azure ML ワークスペースが不要ならリソースグループを削除した
- [ ] Azure Portal のコスト分析で当月の請求額を確認した
