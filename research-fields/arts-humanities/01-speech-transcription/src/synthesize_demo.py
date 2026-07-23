"""Azure TTS でデモ音声 WAV を生成 (書き起こしテスト用)

- 入力: --text または --text-file
- 出力: outputs/sample_ja.wav (16kHz 16bit mono)
- 認証: AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=DEFAULT_TEXT)
    ap.add_argument("--text-file", type=Path)
    ap.add_argument("--voice", default="ja-JP-NanamiNeural")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    load_dotenv()
    if not os.environ.get("AZURE_SPEECH_KEY"):
        sys.exit("[error] AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not set")

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else args.text

    out = args.out or (Path(__file__).resolve().parent.parent / "data" / "sample_ja.wav")
    out.parent.mkdir(exist_ok=True)

    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"],
    )
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
