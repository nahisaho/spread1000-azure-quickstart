# データ

MedMNIST PathMNIST を `medmnist` パッケージが `data/pathmnist.npz` に自動 DL (~205MB, 初回のみ)。

- 出典: Kather et al. (2019) NCT-CRC-HE 100K, PLOS Medicine
- 前処理: Yang et al. (2023) MedMNIST v2, Scientific Data
- ライセンス: **PathMNIST データは CC BY 4.0** (Kather 2019 由来)。`medmnist` **Python パッケージ** (コード) は Apache-2.0。研究・教育利用は自由だが、二次配布時は帰属表示が必須。**注意**: MedMNIST 内の一部データセット (例: DermaMNIST) は CC BY-NC 4.0 (非営利限定) のため、データセットごとに個別確認が必要。
- 詳細: [../docs/02-task.md](../docs/02-task.md)

## 自前病理画像

実 WSI (Camelyon16/PANDA/TCGA) への拡張手順は [../docs/05-your-data.md](../docs/05-your-data.md)。
