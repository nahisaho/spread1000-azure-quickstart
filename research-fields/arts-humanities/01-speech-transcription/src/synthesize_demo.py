"""Azure TTS でデモ音声 WAV を生成 (書き起こしテスト用)

- 入力: --text または --text-file
- 出力: data/sample_ja.wav (16kHz 16bit mono)
- 認証: DefaultAzureCredential (Entra 推奨) または AZURE_SPEECH_KEY + AZURE_SPEECH_REGION

使い方:
  SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
  cd "$SCENARIO_DIR"
  python src/synthesize_demo.py
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


DEFAULT_TEXT = (
    "本研究では、江戸時代後期の古文書に見られる書写文化について、"
    "デジタル人文学の手法を用いて分析を行いました。"
    "多言語エンベディングによる横断検索を実装した結果、"
    "従来困難であった漢文と和文の対応関係を明らかにすることができました。"
)
MAX_TEXT_CHARS = 3000


def _build_speech_config() -> speechsdk.SpeechConfig:
    """Return SpeechConfig, preferring Entra auth over key auth."""
    region = os.environ.get("AZURE_SPEECH_REGION") or os.environ.get("SPEECH_REGION", "")
    key = os.environ.get("AZURE_SPEECH_KEY") or os.environ.get("SPEECH_KEY", "")
    endpoint = os.environ.get("SPEECH_ENDPOINT", "")

    if not region:
        sys.exit("[error] AZURE_SPEECH_REGION / SPEECH_REGION not set (see .env.example)")

    if key:
        if endpoint:
            return speechsdk.SpeechConfig(subscription=key, endpoint=endpoint)
        return speechsdk.SpeechConfig(subscription=key, region=region)

    # Entra path
    try:
        from azure.identity import DefaultAzureCredential  # type: ignore
    except ImportError:
        sys.exit("[error] azure-identity not installed. Run: pip install azure-identity")
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token
    if endpoint:
        return speechsdk.SpeechConfig(auth_token=token, endpoint=endpoint)
    return speechsdk.SpeechConfig(auth_token=token, region=region)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a demo WAV file via Azure TTS for transcription testing."
    )
    ap.add_argument("--text", default=DEFAULT_TEXT, help=f"Text to synthesize (max {MAX_TEXT_CHARS} chars)")
    ap.add_argument("--text-file", type=Path, help="Read text from file instead of --text")
    ap.add_argument("--voice", default="ja-JP-NanamiNeural")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    load_dotenv()

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else args.text
    if not text.strip():
        ap.error("--text / --text-file must not be empty.")
    if len(text) > MAX_TEXT_CHARS:
        ap.error(f"Text length {len(text)} exceeds maximum {MAX_TEXT_CHARS} characters for demo synthesis.")

    out = args.out or (Path(__file__).resolve().parent.parent / "data" / "sample_ja.wav")
    out.parent.mkdir(exist_ok=True)

    speech_config = _build_speech_config()
    speech_config.speech_synthesis_voice_name = args.voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )
    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(out))
    synth = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    print(f"[tts] synthesizing → {out}")
    r = synth.speak_text_async(text).get()
    if r.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        sys.exit(f"[error] TTS failed: {r.reason}")
    print(f"[done] wrote {out} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
