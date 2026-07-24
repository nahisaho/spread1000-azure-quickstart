# requirements-lock/

このディレクトリには Python バージョン・OS 別の **ハッシュ付きピン留め依存関係ファイル** を格納します。

## ファイル命名規則

```
<os>-<accelerator>-py<version>.txt
例: linux-cpu-py312.txt
```

## 生成方法 (pip-tools)

```bash
# pip-tools をインストール
pip install pip-tools

# ロックファイルを生成 (linux-cpu-py312 の場合)
cd "$(git rev-parse --show-toplevel)/research-fields/math-physics-earth/03-gp-regression"
pip-compile \
  --generate-hashes \
  --output-file requirements-lock/linux-cpu-py312.txt \
  requirements.in
```

## インストール

```bash
cd "$(git rev-parse --show-toplevel)/research-fields/math-physics-earth/03-gp-regression"
pip install --require-hashes -r requirements-lock/linux-cpu-py312.txt
```

> **注意**: ロックファイルは Python バージョン・OS が変わると再生成が必要です。
> 異なる環境では対応するロックファイルを使用してください。
