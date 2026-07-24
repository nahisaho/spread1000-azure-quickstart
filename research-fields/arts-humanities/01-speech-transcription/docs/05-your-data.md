# 05 — 自前音声への適用

## 対応フォーマット

Speech SDK は以下を直接受け取ります:

- **WAV**: PCM 16-bit mono 16kHz 推奨 (これ以外は自動リサンプルされるがロス発生)
- **MP3, OGG, FLAC**: `GStreamer` 経由 (Linux/macOS で追加 install 必要)

## 変換 (ffmpeg)

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"

# MP3 → 16kHz 16bit mono WAV
ffmpeg -i interview.mp3 -ar 16000 -ac 1 -sample_fmt s16 data/interview.wav
```

> **権限管理**: `chmod 700 data/ outputs/` および `chmod 600 data/*.wav` を推奨。  
> 機微な音声ファイルは暗号化ストレージ (Azure Disk Encryption / LUKS) に保管してください。

## 長時間音声 (30 分以上)

- `transcribe.py` (continuous recognition) は 30 分を超えるファイルに対して `--allow-long-run` フラグが必要
- **30 分超は Batch Transcription API を推奨** (非同期、大量ファイル向け):

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"
python src/transcribe_batch.py \
    --urls "https://your-storage.blob.core.windows.net/audio/file.wav?<SAS>" \
    --locale ja-JP
```

詳細: https://learn.microsoft.com/azure/ai-services/speech-service/batch-transcription

## 応用例

| ドメイン | 用途 |
|---|---|
| 民俗学 | 高齢者への口述聞き取り、方言採集 |
| 口述史 | 戦後証言、被爆者証言のアーカイブ化 |
| 会話分析 | 教室談話、対話研究 (話者分離必須) |
| 語学教育 | 学習者発話の自動評価 (発音精度スコア) |
| 演劇・音楽 | 舞台音声からのセリフ抽出、字幕化 |

## Custom Speech (専門分野向け精度向上)

- Speech Studio (portal) で `Custom Speech` プロジェクト作成
- テキストデータ (専門用語 CSV) と音声+文字起こしペアを追加
- 学習: ~1 時間、精度は分野特有語彙で 20-40% 改善が典型的
- 詳細: https://learn.microsoft.com/azure/ai-services/speech-service/custom-speech-overview

## Phrase List (カスタム語彙)

人名・学術用語など固有名詞の認識精度を上げるには SDK の `PhraseListGrammar` を使用:

```python
from azure.cognitiveservices.speech import PhraseListGrammar
phrase_list = PhraseListGrammar.from_recognizer(recognizer)
phrase_list.addPhrase("源氏物語")
phrase_list.addPhrase("デジタル人文学")
```

## 話者分離 (Diarization)

対話・複数話者音声は `src/transcribe_diarized.py` を使用:

```bash
SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
cd "$SCENARIO_DIR"
python src/transcribe_diarized.py --audio data/interview.wav
```

`outputs/transcript_diarized.json` にスピーカーID付きセグメントが出力されます。  
**制限**: 最大 240 分、話者重複時は精度低下、話者数の誤推定あり。
