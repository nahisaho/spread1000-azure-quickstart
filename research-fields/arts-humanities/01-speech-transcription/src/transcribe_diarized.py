"""話者分離付き書き起こし — ConversationTranscriber を使用

- 入力: WAV (16kHz 16bit mono 推奨)
- 出力: outputs/transcript_diarized.json
  schema: {"segments": [{"speaker_id": str, "text": str, "offset_ns": int, "duration_ns": int}]}
- 認証: DefaultAzureCredential (Entra 推奨) または AZURE_SPEECH_KEY + AZURE_SPEECH_REGION

制限事項:
  - 1 ファイルあたり最大 240 分 (Batch では制限緩和)
  - 話者が重複して話す場面では分離精度が低下
  - 話者数は自動推定されるが誤推定あり (3-4 名以上で顕著)

使い方:
  SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
  cd "$SCENARIO_DIR"
  python src/transcribe_diarized.py --audio data/sample_ja.wav
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech.transcription import ConversationTranscriber

from _argtypes import existing_file, locale_string, check_audio_duration
from transcribe import SpeechError, _build_speech_config


def transcribe_diarized(
    audio_path: Path,
    language: str = "ja-JP",
    timeout: float = 3600.0,
) -> list[dict]:
    speech_config = _build_speech_config(language)
    audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
    transcriber = ConversationTranscriber(
        speech_config=speech_config, audio_config=audio_config
    )

    segments: list[dict] = []
    done = threading.Event()
    canceled: dict[str, str | None] = {
        "reason": None,
        "error_code": None,
        "error_details": None,
    }

    def _on_transcribed(evt: speechsdk.SpeechRecognitionEventArgs) -> None:
        r = evt.result
        if r.reason == speechsdk.ResultReason.RecognizedSpeech:
            segments.append(
                {
                    "speaker_id": r.speaker_id,
                    "text": r.text,
                    "offset_ns": r.offset,
                    "duration_ns": r.duration,
                }
            )
            offset_sec = r.offset / 1e7
            print(f"  [{offset_sec:6.2f}s] Speaker {r.speaker_id}: {r.text}")

    def _on_session_stopped(evt: speechsdk.SessionEventArgs) -> None:
        done.set()

    def _on_canceled(evt: speechsdk.SpeechRecognitionCanceledEventArgs) -> None:
        canceled.update(
            {
                "reason": str(evt.reason),
                "error_code": str(evt.error_code),
                "error_details": evt.error_details,
            }
        )
        transcriber.stop_transcribing_async()
        done.set()

    transcriber.transcribed.connect(_on_transcribed)
    transcriber.session_stopped.connect(_on_session_stopped)
    transcriber.canceled.connect(_on_canceled)

    print(f"[diarize] starting ConversationTranscriber on {audio_path.name}")
    transcriber.start_transcribing_async().get()

    if not done.wait(timeout=timeout):
        transcriber.stop_transcribing_async()
        raise SpeechError(f"Diarization timed out after {timeout:.0f}s.")

    transcriber.stop_transcribing_async()

    if canceled["reason"] and canceled["reason"] != "CancellationReason.EndOfStream":
        raise SpeechError(f"Transcription canceled: {canceled}")

    if not segments:
        raise SpeechError("No speech recognized (empty diarized transcript).")

    return segments


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe audio with speaker diarization using ConversationTranscriber."
    )
    ap.add_argument("--audio", type=existing_file, required=True,
                    help="Path to audio file (WAV 16kHz recommended)")
    ap.add_argument("--language", default="ja-JP", type=locale_string,
                    help="BCP-47 locale (e.g. ja-JP)")
    ap.add_argument("--timeout", type=float, default=3600.0,
                    help="Max seconds to wait for recognition (default 3600)")
    ap.add_argument("--allow-long-run", action="store_true",
                    help="Bypass 30-min duration cap. Note: diarization accuracy degrades near 240-min limit.")
    args = ap.parse_args()

    load_dotenv()
    check_audio_duration(args.audio, args.allow_long_run)

    segments = transcribe_diarized(args.audio, language=args.language, timeout=args.timeout)

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)
    out_path = outputs / "transcript_diarized.json"
    out_path.write_text(
        json.dumps({"segments": segments}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[done] {len(segments)} segments → {out_path}")


if __name__ == "__main__":
    main()
