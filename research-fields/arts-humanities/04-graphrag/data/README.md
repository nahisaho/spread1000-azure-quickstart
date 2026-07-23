# データ

`data/input/` に 3 つの英語テキスト:
- `01_rangaku.txt` — 蘭学、杉田玄白、解体新書
- `02_meiji_restoration.txt` — 明治維新、薩長同盟、岩倉使節団
- `03_fukuzawa.txt` — 福澤諭吉、慶應義塾、学問のすすめ

**ライセンス**: これらは英語 Wikipedia の該当項目を要約した二次テキストです (CC-BY-SA 3.0/4.0)。学習目的で自由に再利用可能。改変版を配布する場合は同ライセンスで公開してください。

## 自前データへの差し替え

`data/input/` に `.txt` 形式のファイルを配置し、`bash src/run.sh` を再実行してください。詳細は [docs/05-your-data.md](../docs/05-your-data.md)。
