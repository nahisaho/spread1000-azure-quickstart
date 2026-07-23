# トラブルシューティング

## `RuntimeError: element 0 of tensors does not require grad`

- Autograd で二階微分するには、入力 `x`, `t` が `requires_grad=True` である必要があります。
- `compute_pde_residual` 内で `x.clone().requires_grad_(True)` していることを確認してください。
- 一階微分計算時に **`create_graph=True` を忘れると二階微分ができません**。

## L2 誤差が下がらない (5% 以上のまま)

1. `--seed 0` などで別シードを試す (初期化の運)
2. `--w-ic 20 --w-bc 20` で IC/BC 遵守を強化
3. `--epochs 5000` に増やす
4. `src/train.py` の `PINN(hidden=64)` に増やす

## L-BFGS 中に NaN

- Adam の収束が悪すぎるまま L-BFGS に入ると発散します
- 解決: `--epochs` を増やして Adam フェーズを長く

## `import torch` が Windows で失敗

- Visual C++ Redistributable が必要 (Microsoft 公式サイトからダウンロード)
- 「Visual Studio 2015-2022 Redistributable (x64)」をインストール後、Python を再起動

## macOS Apple Silicon で警告が出る

- CPU wheel を使えば `torch.device('cpu')` で問題ありません
- `mps` バックエンドを使う場合、Autograd 二階微分の一部演算がサポートされていない可能性があります。CPU 推奨。

## matplotlib のフォント警告 (日本語)

- 本教材はプロットの日本語文字を使っていません。警告が出ても機能に影響なし。
