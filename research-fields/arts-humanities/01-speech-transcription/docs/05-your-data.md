# 05 — 自前音声への適用

## 対応フォーマット

Speech SDK は以下を直接受け取ります:

- **WAV**: PCM 16-bit mono 16kHz 推奨 (これ以外は自動リサンプルされるがロス発生)
- **MP3, OGG, FLAC**: `GStreamer` 経由 (Linux/macOS で追加 install 必要)

## 変換 (ffmpeg)

```bash
# MP3 → 16kHz 16bit mono WAV
ffmpeg -i interview.mp3 -ar 16000 -ac 1 -sample_fmt s16 interview.wav
```

## 長時間音声 (30 分以上)

- Continuous recognition (本教材) は数時間の音声にも対応、ただしメモリを消費
- **Batch Transcription API** を推奨 (Blob Storage 経由、非同期、大量ファイル向け)
  - https://learn.microsoft.com/azure/ai-services/speech-service/batch-transcription

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

## 話者分離 (Diarization)

対話・複数話者音声は `ConversationTranscriber` に切り替え。1 API 呼び出しで
`Speaker Guest-1: …` 形式のラベル付き結果が得られます。
