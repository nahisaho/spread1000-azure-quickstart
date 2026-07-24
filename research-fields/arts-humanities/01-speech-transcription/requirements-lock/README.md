# requirements-lock

このディレクトリには依存関係のロックファイルを格納します。

## pip-compile でロックファイルを生成する

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"

pip install pip-tools
pip-compile requirements.in --output-file requirements-lock/requirements.txt --strip-extras
```

生成された `requirements-lock/requirements.txt` を使ってインストール:

```bash
pip install -r requirements-lock/requirements.txt
```

開発中は `requirements.in` を編集してから `pip-compile` を再実行してください。
