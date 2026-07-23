# 07 — 倫理・限界・注意事項

## ⚠️ 最重要: 合成データで学んだモデルは実 SEM/STEM に直接適用できません

本クイックスタートは Voronoi + Gaussian ノイズで生成した **完全合成の顕微鏡「相当」画像** を使います。この学習済みモデルを **そのまま実顕微鏡画像に適用しても、多くの場合まともに動作しません**。

理由: 実 SEM/STEM 画像には合成画像に含まれない現象が多数あります。

| 実顕微鏡の現象 | 合成画像で再現できているか |
|---|---|
| ガウスノイズ | ✅ (σ=0.05) |
| 電子チャネリングコントラスト | ❌ |
| チャージング効果 (絶縁体試料) | ❌ |
| ビームダメージ・ドリフト | ❌ |
| 検出器ショットノイズ (Poisson) | ❌ |
| プローブ幾何による不均一照明 | ❌ |
| 菊池線・回折コントラスト | ❌ |

**実運用への正しい道筋**:
1. まずこのクイックスタートで **U-Net 学習パイプラインの動作を理解**
2. 実 SEM/STEM 画像を **50〜200 枚手動アノテート** (ImageJ, Labkit, ilastik など)
3. 本クイックスタートの `MiniUNet` を **転移学習** (合成→実データの fine-tuning)
4. または後述の **実データ用ツール** を使用

## 本クイックスタートの限界

### 科学的限界

- **境界の 1〜2 ピクセル幅仮定**: 実 SEM の粒界は 2〜5 ピクセルの遷移領域を持つことが多い
- **粒界の孤立問題**: 学習後の予測は分断された境界断片になりやすい。ポストプロセスでの skeletonize が必要
- **粒サイズ分布**: 実材料は log-normal などの分布に従うが、合成データは一様分布
- **単一相仮定**: 位相コントラスト・EBSD 相図には対応せず (multi-class にすれば拡張可能)

### 実装上の限界

- **バッチ正規化**: 小バッチ (batch_size=8) では BN が不安定。実データでは `GroupNorm` への変更を検討
- **学習曲線の再現性**: `torch.manual_seed()` だけでは cuBLAS/cuDNN の非決定性は制御しない。完全再現には `torch.use_deterministic_algorithms(True)` が必要
- **クラス不均衡**: `pos_weight=9.0` は Voronoi 用の固定値。実データでは陽性率を実測して調整

## 実運用向けツール (このクイックスタートを超えて)

| ツール | 得意 | URL |
|---|---|---|
| **Trainable Weka Segmentation** (Fiji プラグイン) | 対話的ピクセル分類、EM 顕微鏡 | https://imagej.net/plugins/tws/ |
| **ilastik** | セミオート・マルチカット EM ワークフロー | https://www.ilastik.org/ |
| **CellPose** | インスタンスセグメンテーション、EM 適用可 | https://github.com/MouseLand/cellpose |
| **micro-SAM** | Segment Anything for Microscopy (2024+) | https://github.com/computational-cell-analytics/micro-sam |

## ライセンス

| コンポーネント | ライセンス | 引用要求 |
|---|---|---|
| 本クイックスタートのコード | MIT (リポジトリ準拠) | 任意 |
| PyTorch / torchvision | BSD | — |
| scikit-image | Modified BSD | van der Walt et al. 2014 |
| SciPy | BSD-3 | Virtanen et al. 2020 |
| torchmetrics | Apache 2.0 | — |
| matplotlib | PSF ライク | — |

## 引用義務

論文・発表で本クイックスタートを土台にした学習結果を報告する場合、少なくとも以下を引用してください:

```bibtex
@inproceedings{ronneberger2015unet,
  title={U-Net: Convolutional Networks for Biomedical Image Segmentation},
  author={Ronneberger, Olaf and Fischer, Philipp and Brox, Thomas},
  booktitle={Medical Image Computing and Computer-Assisted Intervention (MICCAI)},
  volume={9351}, pages={234--241}, year={2015},
  doi={10.1007/978-3-319-24574-4_28}, eprint={1505.04597}
}

@article{vanderWalt2014scikitimage,
  title={scikit-image: image processing in {Python}},
  author={{van der Walt}, Stefan and {Sch{\"o}nberger}, Johannes L. and
          {Nunez-Iglesias}, Juan and others},
  journal={PeerJ}, volume={2}, pages={e453}, year={2014},
  doi={10.7717/peerj.453}
}

@article{virtanen2020scipy,
  title={{SciPy 1.0}: Fundamental Algorithms for Scientific Computing in {Python}},
  author={Virtanen, Pauli and Gommers, Ralf and Oliphant, Travis E. and others},
  journal={Nature Methods}, volume={17}, pages={261--272}, year={2020},
  doi={10.1038/s41592-019-0686-2}
}
```

## 責任ある利用

- **合成データで学んだモデルの予測を材料・臨床判断の根拠にしない**
- 実データで検証していない予測を論文・特許の主要主張にしない
- 学習結果を公開する場合、生成条件 (Voronoi 数、ノイズ σ、シード) を明記する
- 予測誤差を人手検証で必ずチェックする
