# 06 — 片付けと次のステップ

## ローカルで完結した場合

Azure リソースは一切作成していないので、**追加の料金は発生しません**。

不要になれば以下を削除して構いません:

```bash
rm -rf data/ outputs/ .venv/
```

- `data/har.zip`, `data/UCI_HAR_Dataset/`, `data/har_windows.npz`: 再実行時に自動で再生成
- `outputs/`: 学習成果物。**別途保存したい場合は先に別ディレクトリへ退避**

## Azure ML を使った場合

[docs/05-azure-ml-t4.md](05-azure-ml-t4.md) の compute を放置しても、`min-instances=0` にしていれば料金は発生しません。それでも不要なら完全削除:

```bash
# compute 削除
az ml compute delete --name gpu-t4 --yes

# ジョブ履歴を保ちたくない場合、実験ごと削除も可能 (通常は不要)
# az ml experiment archive --name spread1000-biosignal
```

保存されたモデル成果物 (`azureml://...`) はワークスペース内のストレージアカウントに残ります。長期保管が不要なら Azure Portal で該当 Blob を削除してください。

## 応用のヒント

### 別のデータセットに置き換える

`src/prepare_data.py` を書き換えれば任意の多チャネル時系列に置き換えられます。ポイント:

1. **入力形状**: `(N, C, T)` 3 次元 float32 テンソルに整形（C = チャネル数、T = 時点数）
2. **被験者 ID を必ず保存**: 分割リークを防ぐため
3. **公式 test 分割**: 存在するなら使う。なければ **被験者独立** に切る (subject 単位で 70/10/20 など)

`src/model.py` の `BiosignalCNN(n_channels=..., n_classes=...)` を新しい次元数に合わせて呼び出せば、モデルはそのまま流用できます。

### 別ドメインへの適用例

| データ | 期待 C | 期待 T | 変更点 |
|---|---:|---:|---|
| 表面 EMG (8ch, 200 Hz, 1 秒窓) | 8 | 200 | `n_channels=8`, kernel はやや大きめ (13 → 9 → 5) |
| EEG (32ch, 250 Hz, 2 秒窓) | 32 | 500 | 更に MaxPool 追加 or GAP 前の時間軸を縮小 |
| モーションキャプチャ (69ch = 23 marker × 3, 60 Hz, 2 秒窓) | 69 | 120 | Conv 入力チャネル増、それ以外は同じ |

いずれの場合も **被験者独立分割** の徹底が最重要です。

### 発展的な手法

CompactCNN で基準精度を出したら、以下を試してみてください:

- **TCN (Temporal Convolutional Network)**: dilation で長距離依存を捉える
- **1D-ResNet**: 深い CNN で表現力を上げる
- **Transformer encoder**: 長時系列に強いが小規模データでは過学習しやすい
- **Multi-task学習**: 活動 + 被験者ID など複数タスクで正則化
- **Self-supervised pretrain**: TS2Vec, TF-C など (小規模データで効くケースあり)

### 医療応用への一般化に必要なこと

**本モデルは医療機器ではありません**（[docs/07-ethics-and-limits.md](07-ethics-and-limits.md) 参照）。研究として発展させる場合:

1. **多施設・多装置・多年齢層データ**での性能検証
2. **subject-independent + site-independent** cross-validation
3. **性能低下要因の分析** (電極位置、装着状態、疾患プロファイル等)
4. **PMDA/FDA/CE の枠組み** に沿った臨床性能評価
5. **説明可能性** (Grad-CAM 相当の 1D 版, SHAP 等) — 医療関係者への説明資料として重要

## 次のシナリオ

- [03: 画像復元 U-Net](../03-image-restoration-unet/) — 電気工学・情報科学分野の画像処理系（準備中）
- 他分野: [ルート README](../../../README.md)
