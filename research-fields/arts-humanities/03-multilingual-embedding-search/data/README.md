# データ

`src/corpus.py` の CORPUS 定数に、5 言語 15 文のデモコーパス (パブリックドメイン文献の要旨相当のオリジナル文) を同梱。

- 日本語 4, 英語 4, フランス語 2, ドイツ語 2, 中国語 3 文
- 話題: 源氏物語、俳句、漱石、Shakespeare、印象派、Goethe、Impressionismus 等

## 自前コーパスへの差し替え

- `src/corpus.py` を編集、または `build_index.py` を書き換えて JSON/CSV から読み込む
- 詳細は [../docs/05-your-data.md](../docs/05-your-data.md)

`data/index.faiss` と `data/index_meta.json` は build 時に自動生成 (gitignore 済み)。
