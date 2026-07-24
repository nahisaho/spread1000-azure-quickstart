# データ

`src/dataset.py::generate()` が合成ハイパースペクトルデータを毎回生成 (乱数シード固定)。外部データダウンロード不要。

- 6 クラス (corn, soybean, wheat, grass_pasture, woods, bare_soil)
- 200 バンド (可視〜近赤外を想定)
- クラスごとに異なる Gaussian ピーク + 白色ノイズ

## 実データへの差し替え

Indian Pines / Salinas / Pavia University 等の実ハイパースペクトルへの切り替え手順は [../docs/05-your-data.md](../docs/05-your-data.md)。
