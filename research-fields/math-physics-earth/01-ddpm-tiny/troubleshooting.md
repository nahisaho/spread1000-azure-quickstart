# トラブルシューティング

## Fashion-MNIST ダウンロード失敗

torchvision は以下のファイルを `data/FashionMNIST/raw/` に配置します。
手動でダウンロードする場合は Zalando ミラーから取得してください:

| ファイル名 | URL | MD5 (torchvision 検証用) |
|---|---|---|
| `train-images-idx3-ubyte.gz` | https://fashion-mnist.s3-website.eu-central-1.amazonaws.com/train-images-idx3-ubyte.gz | `8d4fb7e6c68d591d4c3dfef9ec88bf0d` |
| `train-labels-idx1-ubyte.gz` | https://fashion-mnist.s3-website.eu-central-1.amazonaws.com/train-labels-idx1-ubyte.gz | `25c81989df183df01b3e8a0aad5dffbe` |
| `t10k-images-idx3-ubyte.gz`  | https://fashion-mnist.s3-website.eu-central-1.amazonaws.com/t10k-images-idx3-ubyte.gz  | `bef4ecab320f06d8554ea6380940ec79` |
| `t10k-labels-idx1-ubyte.gz`  | https://fashion-mnist.s3-website.eu-central-1.amazonaws.com/t10k-labels-idx1-ubyte.gz  | `bb300cfdad3c16e7a12a480ee83cd310` |

ダウンロード後の SHA-256 確認:

```bash
sha256sum data/FashionMNIST/raw/*.gz
```

代替ミラー: https://github.com/zalandoresearch/fashion-mnist

## スモークテスト (最小動作確認)

ダウンロード後、以下のコマンドで素早く動作確認できます:

```bash
python src/train.py --n-subset 512 --epochs 2 --seed 42
python src/sample.py --model outputs/ddpm_model.pt --n-samples 4 --seed 0
```

## 生成物が全て真っ黒 / 真っ白

- 学習が全く進んでいない → epoch を増やす、lr を上げる
- Reverse process のスケジューラ実装ミスの可能性 → `src/model.py` の `p_sample_loop` を確認

## MPS (macOS) で NaN

- `--device cpu` に切り替え。MPS は GroupNorm/一部演算で不安定。

## メモリ不足

- `--batch-size 32` に減らす
- `--n-subset 2000` に減らす
