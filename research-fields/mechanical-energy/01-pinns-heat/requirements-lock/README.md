# requirements-lock/

依存パッケージのハッシュ付きロックファイル。`pip install --require-hashes` でサプライチェーン攻撃を防ぎます。

## ファイル

| ファイル | 対象 |
|---|---|
| `linux-cpu-py312.txt` | Linux + CPU + Python 3.12 (pip-compile で自動生成済み) |
| `macos-cpu-py312.txt` | macOS — **macOS 環境で再生成が必要** (下記参照) |
| `windows-cpu-py312.txt` | Windows — **Windows 環境で再生成が必要** (下記参照) |

## インストール

```bash
# Linux:
pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt

# macOS / Windows:
# 各プラットフォームで下記コマンドを実行してロックファイルを生成後、インストール:
pip install pip-tools
pip-compile --generate-hashes \
  --output-file requirements-lock/macos-cpu-py312.txt \
  --strip-extras requirements.in
pip install --require-hashes -r requirements-lock/macos-cpu-py312.txt
```

## 再生成

依存バージョンを更新するときは `requirements.in` を編集し、pip-compile を再実行してください:

```bash
pip-compile --generate-hashes \
  --output-file requirements-lock/linux-cpu-py312.txt \
  --strip-extras requirements.in
```
