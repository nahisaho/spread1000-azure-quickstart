# 03 — 音声準備と書き起こし

## Step 1: デモ音声を生成

自前 WAV がない場合は Azure TTS で作成:

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"
python src/synthesize_demo.py
# → data/sample_ja.wav (16kHz 16bit mono, ~15 秒)
```

好きなテキストで:
```bash
python src/synthesize_demo.py --text "こんにちは、これはテストです。"
python src/synthesize_demo.py --text-file my_script.txt
```

## Step 2: 書き起こし

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"
python src/transcribe.py --audio data/sample_ja.wav
```

## 期待出力

```
[transcribe] starting continuous recognition on sample_ja.wav
  [  0.10s] 本研究では、江戸時代後期の古文書に見られる書写文化について、デジタル人文学の手法を用いて分析を行いました。
  [  9.85s] 多言語エンベディングによる横断検索を実装した結果、従来困難であった漢文と和文の対応関係を明らかにすることができました。

[done] 2 segments → outputs/transcript.txt
```

## CLI オプション

`transcribe.py`:
| フラグ | 既定 | 説明 |
|---|---|---|
| `--audio` | (必須) | 入力音声ファイルパス (存在確認あり) |
| `--language` | `ja-JP` | BCP-47 ロケール (`en-US`, `zh-CN` 等) |
| `--timeout` | `3600` | 認識完了待機の最大秒数 |
| `--allow-long-run` | off | 30 分超の音声を許可 (Batch API 推奨) |

## 出力

- `outputs/transcript.txt` — プレーンテキスト全文
- `outputs/transcript.json` — セグメント別 (offset, duration, confidence, text)
