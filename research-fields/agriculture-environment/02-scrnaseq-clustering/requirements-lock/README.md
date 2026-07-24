# requirements-lock

このディレクトリにはプラットフォーム別のロック済み依存関係ファイルを配置します。

## ロックファイルの生成方法

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/agriculture-environment/02-scrnaseq-clustering"
cd "$SCENARIO_DIR"
test -f src/analyze.py || { echo "wrong dir — aborting"; exit 1; }

# pip-tools を使ってロックファイルを生成
pip install pip-tools
pip-compile requirements.in \
  --output-file requirements-lock/requirements-$(python -c 'import sys,platform; print(f"py{sys.version_info.major}{sys.version_info.minor}-{platform.system().lower()}")').txt \
  --generate-hashes \
  --no-header
```

## ロックファイルを使ったインストール

```bash
pip install -r requirements-lock/requirements-py311-linux.txt  # プラットフォームに合わせて変更
```

## 再生成のタイミング

- `requirements.in` を更新したとき
- Python バージョンを変更したとき
- セキュリティパッチのため依存関係を更新するとき

## ファイル命名規則

`requirements-<pyXY>-<os>.txt`

例: `requirements-py311-linux.txt`, `requirements-py311-windows.txt`
