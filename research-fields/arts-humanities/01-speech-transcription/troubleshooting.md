# トラブルシューティング

## `ImportError: libssl.so.3` (Linux)

```bash
sudo apt install -y libssl-dev
# Ubuntu 24.04 で libasound2 が見つからない場合:
sudo apt install -y libasound2t64
```

## `AZURE_SPEECH_KEY not set`

`.env` ファイルの存在と内容を確認 (キーを echo しない):
```bash
stat -c '%a %n' .env   # パーミッションが 600 であることを確認
# Entra 認証を使っている場合はキー不要 (az login 済みか確認)
```

## `USP.HTTP.ERROR: 401 Unauthorized`

- キーが間違っている (Portal で `KEY 1` を再確認)
- リージョンが間違っている (`japaneast` vs `japanwest` 等)

## 認識結果が空

- 音声ファイルが 16kHz mono か: `ffprobe sample.wav` で確認
- 無音区間だけの WAV になっていないか (`ffplay sample.wav` で聴く)
- `--language ja-JP` を明示

## `SPXERR_TIMEOUT`

- ネットワーク不安定、または長時間無音 → SDK が session 停止を判断
- 通常は自動再接続、必要なら `speech_config.set_property(SpeechServiceConnection_RecognitionMode, "INTERACTIVE")` を試す

## TTS 音声が不自然

- `--voice ja-JP-NanamiNeural` が既定。他候補:
  - `ja-JP-KeitaNeural` (男性)
  - `ja-JP-DaichiNeural`, `ja-JP-AoiNeural` 等
- 全一覧: `az cognitiveservices account list-skus --kind SpeechServices --location japaneast`  
  または SDK: `speech_synthesizer.get_voices_async().get()`  
  または REST: `GET https://<region>.tts.speech.microsoft.com/cognitiveservices/voices/list`
