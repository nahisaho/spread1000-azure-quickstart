# 01 — 拡散モデル (DDPM) 最小実装

**対象**: 拡散モデル (Diffusion / DDPM) を数式レベルで理解したい数物・地球系研究者
**目標**: Fashion-MNIST を 16×16 にダウンサンプルし、**Tiny U-Net + DDPM** を CPU で 5〜10 分学習し、ノイズから画像を生成する forward/reverse process を体験
**手法**: Ho et al. 2020 の DDPM を最小実装 (~500K params, T=200 timesteps)

> [!NOTE]
> 完全にローカル CPU 完結。CIFAR や 256×256 のような大サイズは扱わず、**「動く最小」に振り切った教材**です。

## 全体像

```
src/train.py --epochs 10 --device cpu

   ├→ Forward process q(x_t | x_0): 元画像に段階的にノイズ付加
   │    x_t = √(ᾱ_t) x_0 + √(1 - ᾱ_t) ε,  ε ~ N(0, I)
   │
   ├→ Tiny U-Net ε_θ(x_t, t) がノイズを予測 (~500K params)
   │    loss = ||ε - ε_θ(x_t, t)||²
   │
   └→ outputs/
        ├── ddpm_model.pt
        ├── loss_curve.png
        └── samples.png   # T ステップ逆拡散でノイズから 16 枚生成
```

## クイックスタート

```bash
cd research-fields/math-physics-earth/01-ddpm-tiny

python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.in

python src/train.py --epochs 10 --device cpu --seed 42
python src/sample.py --model outputs/ddpm_model.pt --n-samples 16 --seed 42
```

## タスク

- **元データ**: Fashion-MNIST 28×28 グレースケール → 16×16 にリサイズ
- **時間ステップ**: T = 200
- **ノイズスケジューラ**: cosine schedule (Nichol & Dhariwal 2021, T=200, 末端 SNR ≈ 0)
- **モデル**: Tiny U-Net (~500K params) with sinusoidal timestep embedding

## ドキュメント

1. [前提条件](docs/01-prerequisites.md)
2. [DDPM 数式](docs/02-ddpm-math.md) — forward / reverse process
3. [学習](docs/03-train.md)
4. [結果と生成品質](docs/04-understand-results.md)
5. [拡張](docs/05-extending.md) — CFG, EDM, latent diffusion への道
6. [片付け](docs/06-cleanup.md)
7. [倫理と限界](docs/07-ethics-and-limits.md)

トラブル対応: [troubleshooting.md](troubleshooting.md)

## ライセンス

- Fashion-MNIST: MIT (Zalando Research)
- コード: リポジトリのライセンス

## 免責

**本教材は拡散モデル数式理解のための最小実装。生成品質は Stable Diffusion 等の実用モデルと比較にならず、生成物 (16×16 グレースケール) を実応用に用いるものではありません。**
