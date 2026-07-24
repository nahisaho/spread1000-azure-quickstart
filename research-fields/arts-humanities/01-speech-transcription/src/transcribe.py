"""Azure Speech SDK で日本語音声を書き起こし

- 入力: WAV (16kHz 16bit mono 推奨)
- 出力: outputs/transcript.txt + outputs/transcript.json (詳細メタ)
- 認証: DefaultAzureCredential (Entra 推奨) または AZURE_SPEECH_KEY + AZURE_SPEECH_REGION

使い方:
  SCENARIO_DIR="$(git rev-parse --show-toplevel)/research-fields/arts-humanities/01-speech-transcription"
  cd "$SCENARIO_DIR"
  python src/transcribe.py --audio data/sample_ja.wav
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

from _argtypes import existing_file, locale_string, check_audio_duration


class SpeechError(RuntimeError):
    """Raised when recognition fails or produces no output."""


def _build_speech_config(language: str) -> speechsdk.SpeechConfig:
    """Return a SpeechConfig, preferring Entra (token) auth over key auth."""
    region = os.environ.get("AZURE_SPEECH_REGION") or os.environ.get("SPEECH_REGION", "")
    key = os.environ.get("AZURE_SPEECH_KEY") or os.environ.get("SPEECH_KEY", "")
    endpoint = os.environ.get("SPEECH_ENDPOINT", "")

    if not region:
        sys.exit("[error] AZURE_SPEECH_REGION / SPEECH_REGION not set (see .env.example)")

    if key:
        if endpoint:
            cfg = speechsdk.SpeechConfig(subscription=key, endpoint=endpoint)
        else:
            cfg = speechsdk.SpeechConfig(subscription=key, region=region)
    else:
        # Entra: obtain token via DefaultAzureCredential
        try:
            from azure.identity import DefaultAzureCredential  # type: ignore
        except ImportError:
            sys.exit("[error] azure-identity not installed. Run: pip install azure-identity")
        credential = DefaultAzureCredential()
        token = credential.get_token("https://cognitiveservices.azure.com/.default").token
        if endpoint:
            cfg = speechsdk.SpeechConfig(auth_token=token, endpoint=endpoint)
        else:
            cfg = speechsdk.SpeechConfig(auth_token=token, region=region)

    cfg.speech_recognition_language = language
    cfg.output_format = speechsdk.OutputFormat.Detailed
    cfg.set_profanity(speechsdk.ProfanityOption.Raw)
    return cfg


def transcribe_file(audio_path: Path, language: str = "ja-JP", timeout: float = 3600.0) -> dict:
    speech_config = _build_speech_config(language)
    audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )

    results: list[dict] = []
    done = threading.Event()
    canceled: dict[str, str | None] = {
        "reason": None,
        "error_code": None,
        "error_details": None,
    }

    def on_recognized(evt: speechsdk.SpeechRecognitionEventArgs) -> None:
        r = evt.result
        if r.reason == speechsdk.ResultReason.RecognizedSpeech:
            entry: dict = {
                "text": r.text,
                "offset_sec": r.offset / 1e7,
                "duration_sec": r.duration / 1e7,
            }
            try:
                detail = json.loads(r.json)
                entry["confidence"] = detail.get("NBest", [{}])[0].get("Confidence")
            except Exception:
                pass
            results.append(entry)
            print(f"  [{entry['offset_sec']:6.2f}s] {r.text}")

    def on_session_stopped(evt: speechsdk.SessionEventArgs) -> None:
        done.set()

    def _on_canceled(evt: speechsdk.SpeechRecognitionCanceledEventArgs) -> None:
        canceled.update(
            {
                "reason": str(evt.reason),
                "error_code": str(evt.error_code),
                "error_details": evt.error_details,
            }
        )
        speech_recognizer.stop_continuous_recognition()
        done.set()

    speech_recognizer.recognized.connect(on_recognized)
    speech_recognizer.session_stopped.connect(on_session_stopped)
    speech_recognizer.canceled.connect(_on_canceled)

    print(f"[transcribe] starting continuous recognition on {audio_path.name}")
    speech_recognizer.start_continuous_recognition()

    if not done.wait(timeout=timeout):
        speech_recognizer.stop_continuous_recognition()
        raise SpeechError(f"Recognition timed out after {timeout:.0f}s.")

    # end-of-stream is normal completion; any other cancellation reason is an error
    if canceled["reason"] and canceled["reason"] != "CancellationReason.EndOfStream":
        raise SpeechError(f"Recognition canceled: {canceled}")

    full_text = " ".join(r["text"] for r in results)
    if not full_text.strip():
        raise SpeechError("No speech recognized (empty transcript).")

    return {
        "audio_file": str(audio_path),
        "language": language,
        "segments": results,
        "full_text": full_text,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transcribe a local audio file using Azure Speech continuous recognition."
    )
    ap.add_argument("--audio", type=existing_file, required=True, help="Path to audio file (WAV recommended 16kHz)")
    ap.add_argument("--language", default="ja-JP", type=locale_string, help="BCP-47 locale (e.g. ja-JP)")
    ap.add_argument("--timeout", type=float, default=3600.0, help="Max seconds to wait for recognition (default 3600)")
    ap.add_argument(
        "--allow-long-run",
        action="store_true",
        help="Bypass the 30-min duration cap check. For files > 30 min, consider --batch (transcribe_batch.py).",
    )
    args = ap.parse_args()

    load_dotenv()

    check_audio_duration(args.audio, args.allow_long_run)

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    result = transcribe_file(args.audio, language=args.language, timeout=args.timeout)
    (outputs / "transcript.txt").write_text(result["full_text"], encoding="utf-8")
    (outputs / "transcript.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[done] {len(result['segments'])} segments → outputs/transcript.txt")


if __name__ == "__main__":
    main()
