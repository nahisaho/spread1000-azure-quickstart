# トラブルシューティング

## Materials Project API

### `MPRestError: 401 Unauthorized`

- API キー未設定または誤り。https://next-gen.materialsproject.org/dashboard で確認
- 環境変数を確認する際は **キーそのものを表示しないでください** (画面共有・スクリーンショットで漏洩する事故が多発しています):
  ```bash
  # 良い例: 値ではなく「設定されているか」だけを確認
  test -n "${MP_API_KEY:-}" && echo "MP_API_KEY is set (length=${#MP_API_KEY})" \
                            || echo "MP_API_KEY is missing"
  # 悪い例: `echo $MP_API_KEY` はキーそのものをターミナル履歴に残す
  ```
- 旧レガシー API (`https://materialsproject.org/rest/`) のキーは新 API では使えません。新 API 用に再生成してください

### `429 Too Many Requests`

- MP API は**リクエスト頻度 (req/s)** に対して制限がかかります (公式ドキュメント上限)
- `chunk_size` を大きくすると 1 リクエストあたりの取得件数が増え、総リクエスト数はむしろ**減ります** — したがって `429` を防ぐには `chunk_size` を維持したまま**並列実行を減らす・リトライ間隔を空ける**のが正解です
- `fetch_data.py` は `mp-api` クライアント標準のバックオフに従います。それでも 429 が続く場合は数分待ってから再試行してください
- 大量ダウンロードが目的なら [MP 公式の bulk download 手順](https://docs.materialsproject.org/downloading-data) を使い、API を叩き続けないでください

### `search()` が空の結果を返す

- 条件が厳しすぎる可能性。`num_elements=(1, 4)` に緩めるか `band_gap=(0.0, 6.0)` に広げる
- `include_gnome` は `False` のまま (CC BY-NC ライセンスなので公開教材では除外)

## matminer / pymatgen

### `ImportError: cannot import name 'ElementProperty'`

- matminer 0.10.1 では `matminer.featurizers.composition.ElementProperty` に配置
- `pip install --upgrade matminer` で最新版に

### `ValueError: too many values to unpack` (numpy 2.x 系)

- pymatgen / matminer の互換性を確認: `pip install --upgrade pymatgen matminer`
- Python 3.13 で失敗する場合は 3.12 に切り替え (matminer の公式 classifier は 3.11/3.12)

### `Featurizer.featurize()` が NaN を含む

- 一部の元素 (放射性元素など) は Magpie 事典に含まれない場合があります
- `featurize.py` は NaN 行を落とすオプションを備え、既定で削除して警告を出します

## XGBoost

### `xgboost.core.XGBoostError: Check failed: n_targets`

- ターゲット (band_gap) 列が NaN のみになっていないか確認
- `pd.read_parquet(...).describe()` で列統計を確認

### GPU を使いたい

- CPU 版で十分ですが、大規模データで GPU を試す場合は `pip install xgboost` (無印) に置き換え、`XGBRegressor(device="cuda")` を指定

## Azure

### Cloud Shell が 20 分でタイムアウト

- 長い 5-fold CV では途中で切れることがあります
- ローカル (WSL2) または AML Compute Instance の利用を推奨
- Cloud Shell では `nohup python src/train.py &` で継続実行し `disown` する運用は非推奨 (状態が失われます)

### AML Compute Instance が起動しない

- クォータ不足の可能性: `az ml compute list-usage --resource-group <rg> --workspace-name <ws> -o table` (`--resource-group` は現行 CLI で必須)
- Standard_E2s_v3 が Japan East で 2 vCPU 分空いているか確認
