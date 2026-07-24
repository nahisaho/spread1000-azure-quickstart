# ロックファイル生成手順

依存関係の完全なピンとハッシュ検証には pip-tools を使用してください。

## 前提

```bash
pip install pip-tools
```

## プラットフォーム別の生成手順

### Linux (Python 3.12, CPU)

```bash
pip-compile --generate-hashes requirements.in \
  -o requirements-lock/linux-cpu-py312.txt
```

### macOS (Python 3.12, CPU)

```bash
pip-compile --generate-hashes requirements.in \
  -o requirements-lock/macos-cpu-py312.txt
```

### Windows (Python 3.12, CPU)

```powershell
pip-compile --generate-hashes requirements.in `
  -o requirements-lock/windows-cpu-py312.txt
```

## インストール (ロックファイル使用時)

```bash
# torch を先にインストール (CPU wheel)
pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cpu

# ロックファイルからハッシュ検証付きでインストール
pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt
```

## 注意

- torch 本体は PyTorch の独自 wheel サーバーからダウンロードするため、
  pip-compile の `--generate-hashes` 対象外です。torch の SHA-256 は
  PyTorch 公式リリースノートで確認してください。
- ロックファイルはプラットフォーム・Python バージョンごとに異なります。
  CI/CD では対象プラットフォームで再生成してください。
- 現在このディレクトリにはロックファイルが含まれていません。
  ネットワーク環境で上記の手順を実行して生成してください。
