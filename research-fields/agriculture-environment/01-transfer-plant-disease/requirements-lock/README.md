# requirements-lock — 依存関係の固定

再現性のため、ハッシュ付きのロックファイルを生成して使用することを推奨します (MED 10)。

## ロックファイルの生成方法

```bash
pip install pip-tools

# ロックファイルを生成 (ハッシュ付き)
pip-compile ../requirements.in \
  --generate-hashes \
  --output-file requirements.txt

# ロックファイルからインストール
pip install -r requirements-lock/requirements.txt
```

## torch / torchvision の固定

torch と torchvision は先に CPU wheel を別途インストールしてからロックファイルを生成してください:

```bash
pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
pip-compile ../requirements.in --generate-hashes --output-file requirements.txt
```

## ロックファイルのコミット

生成後、`requirements-lock/requirements.txt` をリポジトリにコミットすることで、
チーム全員が同じバージョンを使用できます。

```bash
git add requirements-lock/requirements.txt
git commit -m "chore: lock Python dependencies"
```
