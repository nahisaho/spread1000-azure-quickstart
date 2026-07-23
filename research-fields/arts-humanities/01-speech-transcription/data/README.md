# データ

このシナリオは **音声データを含みません** (すべて `.gitignore` 対象)。

デモ音声は `src/synthesize_demo.py` で毎回 Azure TTS から生成できます (`data/sample_ja.wav`)。

## 自前音声を使う場合

- 16kHz 16bit mono WAV 推奨
- MP3/M4A の場合は `ffmpeg -i src.m4a -ar 16000 -ac 1 -sample_fmt s16 out.wav`
- 詳細は [../docs/05-your-data.md](../docs/05-your-data.md)

## 音声の匿名化

固有名詞のマスキング、話者匿名化は **事前に行う** ことを推奨 (IRB 標準要件)。
