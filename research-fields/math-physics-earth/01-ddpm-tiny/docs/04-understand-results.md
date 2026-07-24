# 04 — 結果と生成品質

## samples.png の見方

- 4×4 グリッドの 16×16 画像
- 学習不十分 → ノイズのまま or 一色
- 学習成功 → **服の輪郭がぼんやりと現れる** (Fashion-MNIST の 10 クラスがぼんやり区別できる)
- 10 epoch では大まかな形状のみ、20〜50 epoch でよりはっきりする

## loss_curve.png

- MSE loss は typically 0.3 → 0.1 に減衰
- グラフには **train loss** と **val_denoising_mse** の両方が表示される
  - `val_denoising_mse`: サブセット 10% の検証セットで毎 epoch 計測 (決定論的ノイズ)
- 停滞したら `--lr 1e-4` に落として **`--resume outputs/ddpm_model.pt`** で再開

> **⚠️ FashionMNIST テストセット (test split) は使用しない**
> 学習にも検証にも FashionMNIST の `train=False` テストセットは使用しません。
> 公正な評価のために温存してください。本教材のサブセット分割と val 評価は
> `train=True` 側の 90/10 分割で完結します。

## 品質の限界

- **16×16 なので細部は原理的に出せない**
- Fashion-MNIST の 10 クラスを 4000 枚だけで学習しているので、モード崩壊もある
- 実用画像生成には CIFAR (32×32) を EDM/DiT で数時間、あるいは Stable Diffusion 相当が必要

## 追加でできること

- `sample.py --seed 0` vs `--seed 1` で **異なるランダムシードから異なる生成物**が得られることを確認
- `T` を 200 → 100 に半減させると生成が高速だが品質低下
- t=0 と t=T-1 の中間で `x_t` を可視化すると forward process が体験できる
