# 07 — 倫理と限界

## 「法則発見」の主張は慎重に

- GP はデータを最も MAE 良くフィットする式を返すだけ
- **偶然一致した式** と **真の物理法則** は区別できない
- 発見式は必ず:
  1. 独立データ (別のシードで生成、別の実験、外挿点) で検証
  2. 次元解析で妥当性チェック
  3. 既知の物理則との整合性を確認
  4. 可能なら理論的導出も試みる

## 外挿の危険

- GP は学習データ範囲外で振る舞い不定
- ケプラー例で $a \in [0.4, 30]$ AU で学習 → $a = 100$ AU に外挿すると意味不明な値になり得る

## 未観測変数の欠落

- 系に効いているが観測していない変数があると、他の変数に無理やり押し込んだ式ができる (spurious correlation)

## サンプル効率

- 200 点でも十分な問題もあれば、10000 点必要な問題もある
- **観測ノイズが大きい** ほど発見難易度が上がる

## 参考文献

- Koza, J. R. (1992). *"Genetic Programming: On the Programming of Computers by Means of Natural Selection"*, MIT Press
- Schmidt & Lipson (2009). *"Distilling free-form natural laws from experimental data"*, Science 324
- Cranmer et al. (2020). *"Discovering Symbolic Models from Deep Learning with Inductive Biases"*, NeurIPS
