# 06. 倫理と限界

## Materials Project データのライセンス

- **コアデータ**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — 帰属表示すれば再配布・改変・商用利用可
- **GNoME (Google DeepMind 提供の 117,000 材料)**: **CC BY-NC** — 商用不可、教材への直接再配布に注意
- **本教材は `include_gnome=False` を既定**にしているため、生成された Parquet は CC BY 4.0 相当で扱えます

引用 (必須):

> Jain, A., Ong, S. P., Hautier, G. et al. Commentary: The Materials Project: A materials genome approach to accelerating materials innovation. **APL Materials** 1, 011002 (2013). DOI: [10.1063/1.4812323](https://doi.org/10.1063/1.4812323)

## API キーの取り扱い

- **API キーは秘密情報**です。`.env` や設定ファイルにコミットしないでください
- Git 履歴に混入した場合は revoke → git-filter-repo で履歴書き換え
- 本教材の `.gitignore` は `.env` を除外済み

## 予測モデルの適用範囲

XGBoost + Magpie による band gap 回帰は以下の**厳しい限界**があります:

1. **DFT 由来の学習ターゲット**: MP の band gap は PBE / GGA / GGA+U で計算されており、**実験値より系統的に低くなる傾向 (bandgap underestimation)** が知られています。誤差の大きさは化学系・磁性状態・材料ごとに大きく異なり、一律の補正値 (「0.5〜1.5 eV 足す」など) は科学的に正当化できません。実験値予測には HSE / G0W0 / 実験ベンチマークとの再校正が必要です
2. **band_gap = 0.1〜5.0 eV に絞った学習データ**: 本教材は既定で **金属 (0 eV) と広い禁制帯の絶縁体 (>5 eV) を除外**して学習します。よって出来上がるモデルは「あらかじめ半導体だと分かっている材料」のバンドギャップを推定する用途に限定されます。任意材料のスクリーニングに使う場合は、事前に「金属 / 半導体」分類器を通す 2 段構成にするか、フィルタ条件そのものを広げて再学習してください
3. **周期的無機結晶に限定**: 学習データは MP の DFT 最適化済み結晶。**分子結晶、アモルファス、表面、界面、有機分子**には適用外
4. **元素数フィルタ**: 既定 1〜3 元素。4 元素以上の高エントロピー材料や合金は対象外
5. **組成のみの特徴量**: 同一組成の多形 (α相/β相など) を区別できません。より高精度が必要なら結晶構造ベースの featurizer (SineCoulombMatrix, CrystalNNFingerprint) や GNN (MEGNet, ALIGNN, M3GNet) を検討
6. **合成可能性の判断はできません**: DFT 上安定でも実際に合成できるとは限りません

## 参考文献 (適用範囲を検討する際に)

- Ward et al. (2016) "A general-purpose machine learning framework for predicting properties of inorganic materials." *npj Comput. Mater.* 2, 16028. [DOI](https://doi.org/10.1038/npjcompumats.2016.28)
- Dunn et al. (2020) "Benchmarking materials property prediction methods: the Matbench test set and Automatminer reference algorithm." *npj Comput. Mater.* 6, 138. [DOI](https://doi.org/10.1038/s41524-020-00406-3)
- Deng et al. (2023) "CHGNet as a pretrained universal neural network potential for charge-informed atomistic modelling." *Nat. Mach. Intell.* 5, 1031-1041. [DOI](https://doi.org/10.1038/s42256-023-00716-3)

## 責任ある使用

- 予測値を単独の根拠として材料合成や産業判断を行わないでください
- **危険物・エネルギー材料 (爆薬・推進剤・自己反応性物質)・放射性化合物・毒性の高い化合物**を対象に含める場合は、必ず所属機関の安全管理部門・専門家レビュー・法令 (火薬類取締法、毒劇物取締法、原子炉等規制法など) を通してください。機械学習による初期スクリーニング結果を「合成推奨」の根拠として単独で使わないこと
- 研究発表では**モデル・特徴量・データ取得日・データ件数・CV スコア + ホールドアウト評価 + `data/metrics.json` の `package_versions`** を明記
- 引用と適用範囲を明示すること

## 参考 (Azure / AI 倫理)

- [経済産業省・総務省『AI 事業者ガイドライン (第1.0版)』](https://www.meti.go.jp/press/2024/04/20240419004/20240419004.html)
- [Azure OpenAI Responsible AI 実装ガイド](https://learn.microsoft.com/azure/ai-foundry/responsible-ai/openai/overview) — 本教材は OpenAI を使いませんが、AI モデルの責任ある運用の一般論として
