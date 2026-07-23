# 01 — 音声書き起こし (Azure Speech to Text)

**分野**: 民俗学フィールドワーク、口述史、談話分析、外国語教育、口承文学  
**手法**: Azure AI Speech の continuous recognition (Japanese)  
**時間**: ~5 分 (リソース作成含む)

## 何が学べるか

- Azure Portal で Speech リソースを 1 分で作成
- Azure Speech SDK Python の使い方
- TTS で自作デモ音声 → STT で書き起こしの往復テスト
- タイムスタンプ + 信頼度付きの詳細出力の取得

## リソース準備

Azure Portal で以下を作成 (1 リソースのみ):

1. **Speech Services** リソース (Standard S0, japaneast など)
2. `Keys and Endpoint` からキーとリージョンをコピー
3. `.env` を作成:

```bash
cp .env.example .env
# .env を編集して KEY と REGION を設定
```

## 使い方

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 1) デモ音声を Azure TTS で生成 (data/sample_ja.wav)
python src/synthesize_demo.py

# 2) その音声を STT で書き起こし
python src/transcribe.py --audio data/sample_ja.wav
```

## コスト

| 項目 | 従量 |
|---|---|
| Speech Standard S0 STT | $1.00 / 1 時間音声 |
| Speech Neural TTS | $16 / 100 万文字 |
| **本デモ (30 秒音声 × TTS+STT)** | **$0.01 未満** |

リソースは**存在するだけでは無課金** (トークン/秒数のみ課金)。

## ドキュメント

- [01 前提条件](docs/01-prerequisites.md)
- [02 Azure リソース準備](docs/02-provision.md)
- [03 音声準備と書き起こし](docs/03-run.md)
- [04 出力の解釈](docs/04-understand-results.md)
- [05 自前音声への適用](docs/05-your-data.md)
- [06 片付け](docs/06-cleanup.md)
- [07 倫理と限界](docs/07-ethics-and-limits.md)
- [トラブルシューティング](troubleshooting.md)
