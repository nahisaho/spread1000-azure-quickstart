# 01 — 前提条件

- Python 3.10+
- Azure サブスクリプション
- Azure OpenAI 利用申請が承認済み
- Bash 環境

## Python 環境

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 対応入力ファイル

- **PDF** (born-digital, スキャン画像 PDF どちらも)
- **JPEG, PNG, TIFF, BMP, HEIF**
- 最大 500 MB / 2000 ページ / 10000×10000 ピクセル

古文書は通常スキャン画像 PDF なので、Document Intelligence の OCR 能力に依存します。
