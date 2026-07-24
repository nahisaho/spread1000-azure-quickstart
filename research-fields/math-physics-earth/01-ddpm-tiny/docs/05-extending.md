# 05 — 拡張

## CFG (Classifier-Free Guidance)

- クラスラベルを条件入力に追加 → 条件付き生成
- 学習時は 10% の確率でラベルをドロップして無条件学習も同時に
- サンプル時: `eps = eps_uncond + w * (eps_cond - eps_uncond)`, w > 1 で品質向上

## EDM / DDIM

- **DDIM** (Song 2021): 決定的サンプリングで T を 50 程度まで削減しても品質維持
- **EDM** (Karras et al. 2022): ノイズレベルに直接パラメタライズされた設計空間 + preconditioning + 学習重み設計 + サンプラー設計のフレームワーク. VP/VE SDE と直交する切り口

## Latent Diffusion (Stable Diffusion)

- VAE で画像を潜在空間 (64×64×4 など) に圧縮 → その中で DDPM
- 元解像度が 512×512 でも計算量が 1/64 程度に

## 科学応用

- **分子構造生成**: 拡散モデルは 3D 座標にも拡張可 (EDM-based diffusion)
- **天体観測データのデノイジング / 補完**: 拡散モデルの conditional prior として
- **気象データダウンスケーリング**: 低解像度 → 高解像度予測

## 実装参考

- Hugging Face `diffusers` ライブラリ: 実プロダクション用。教材でここまで理解できていれば読める。
- CompVis / stability-ai の Stable Diffusion 実装 → 本教材はこの最小版
