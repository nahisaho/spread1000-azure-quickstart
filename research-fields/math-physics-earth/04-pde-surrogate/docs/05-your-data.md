# 05 — 実データへの拡張

## 実気象データ (ERA5)

**ERA5** (ECMWF 再解析):
- 0.25° グリッド (~721×1440)、1979-現在、37 気圧面
- 気温、風速、気圧、湿度、降水など数十変数
- 入手: **Climate Data Store (CDS)** or Google Cloud Public Datasets
- 単純学習でも数 TB、Azure Storage Blob 推奨

## Weather Bench 2

- 気象サロゲート評価の標準ベンチマーク: https://weatherbench2.readthedocs.io/
- ERA5 の縮約版 + 予測モデル比較インフラ
- FourCastNet, GraphCast 等はここでスコア公開

## 他 PDE データセット

| データセット | PDE 種別 | 入手 |
|---|---|---|
| **PDEBench** | Burgers, Navier-Stokes, diffusion-reaction | https://github.com/pdebench/PDEBench |
| **The Well** | 15 種の物理シミュレーション | https://github.com/PolymathicAI/the_well |
| **PDEArena** | 2D Navier-Stokes, Maxwell | https://github.com/microsoft/pdearena |

## 差し替え手順

`src/pde.py` を実データローダに置換:
```python
def load_era5_slice(path, variables=["u10", "v10"], time_range=("2000", "2020")):
    import xarray as xr
    ds = xr.open_zarr(path).sel(time=slice(*time_range))
    return ds[variables].to_array().values  # shape (var, time, lat, lon)
```

## モデルのスケールアップ

- **base=32 or 64** に増やす (~500K〜2M params)
- **ViT/FNO** に置き換えて大規模データ対応
- Azure ML の GPU クラスター (T4/A100) で学習

## Azure Storage 活用

- **Blob Storage** に ERA5 zarr データを配置
- `azcopy` で高速転送
- Azure ML Pipeline で分散学習

## 応用シナリオ

- **短時間降水予報 (nowcasting)**: 数分先の降水分布予測
- **海面高度異常予測**: エルニーニョ監視
- **プラズマ乱流サロゲート**: ITER のシミュレーション代替
- **CO2 拡散モデル**: 大気汚染源特定

## 参考文献

- Rasp et al. (2023). *"WeatherBench 2: A benchmark for the next generation of data-driven global weather models"*
- Pathak et al. (2022). *"FourCastNet"*, arXiv
- Lam et al. (2023). *"Learning skillful medium-range global weather forecasting"* (GraphCast), Science
- Kochkov et al. (2024). *"Neural general circulation models for weather and climate"*, Nature
