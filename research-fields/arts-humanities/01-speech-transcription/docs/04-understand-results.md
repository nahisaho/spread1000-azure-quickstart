# 04 — 出力の解釈

## transcript.json のスキーマ

```json
{
  "audio_file": "data/sample_ja.wav",
  "language": "ja-JP",
  "segments": [
    {"text": "…", "offset_sec": 0.10, "duration_sec": 9.55, "confidence": 0.93},
    ...
  ],
  "full_text": "…"
}
```

- **offset_sec**: セグメント開始時刻 (秒)
- **duration_sec**: セグメント長
- **confidence**: 0-1 の信頼度。< 0.7 なら手動確認推奨

## セグメント分割の挙動

- 250ms 以上の無音でセグメント分割 (デフォルト)
- 「あの」「えー」などのフィラーもそのまま入る (プロファニティフィルタ Raw 設定)
- カスタム語彙 (人名/学術用語) を追加したい場合は Speech Studio で **Phrase List** を作成

## 認識精度に影響する要因

| 要因 | 影響 | 対策 |
|---|---|---|
| サンプルレート | 8kHz 電話音声だと精度落ちる | 16kHz 以上を推奨 |
| 環境雑音 | 大きく低下 | ノイズ除去前処理 (Audition, RNNoise) |
| 方言 | やや低下 | Custom Speech で方言データ学習 |
| 話者交代 | 混ざる | Speaker Diarization を有効化 (下記) |
| 専門用語 | 低下 | Phrase List / Custom Speech |

## 話者分離を有効化するには

`transcribe.py` を編集して:

```python
speech_config.set_property(
    speechsdk.PropertyId.SpeechServiceResponse_DiarizeIntermediateResults, "true"
)
# または ConversationTranscriber を使う (推奨)
transcriber = speechsdk.transcription.ConversationTranscriber(...)
```

詳細: https://learn.microsoft.com/azure/ai-services/speech-service/get-started-stt-diarization
