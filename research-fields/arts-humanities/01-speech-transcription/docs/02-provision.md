# 02 — Azure リソース準備

## Portal で作成 (推奨、1 分)

1. Azure Portal で [Create a resource] → `Speech services` を検索
2. 設定:
   - **Resource group**: 新規作成 (例: `rg-speech-demo`)
   - **Region**: `Japan East` (日本語音声の低レイテンシ、東京拠点向け)
   - **Pricing tier**: `Standard S0` (Free F0 でも動くが 1 リクエスト/秒制限)
3. 作成完了後、`Keys and Endpoint` → `KEY 1` と `Location/Region` をコピー
4. プロジェクト直下に `.env`:

```
AZURE_SPEECH_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_SPEECH_REGION=japaneast
```

## CLI で作成 (Bash)

```bash
RG=rg-speech-demo
LOC=japaneast
NAME=spread-speech-$RANDOM

az group create -n $RG -l $LOC
az cognitiveservices account create \
  -n $NAME -g $RG -l $LOC \
  --kind SpeechServices \
  --sku S0 \
  --yes

az cognitiveservices account keys list -n $NAME -g $RG --query key1 -o tsv
```

## 料金 (japaneast 標準)

| 機能 | 単価 |
|---|---|
| STT Standard | $1.00 / 音声時間 |
| STT Batch | $0.60 / 音声時間 |
| TTS Neural | $16 / 100 万文字 |
| Custom Neural Voice (学習) | $52 / hour |

**存在するだけでは無課金**、実際に使ったぶんのみ。
