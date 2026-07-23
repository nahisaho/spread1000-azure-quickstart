"""Azure Speech SDK で日本語音声を書き起こし

- 入力: WAV (16kHz 16bit mono 推奨)
- 出力: outputs/transcript.txt + outputs/transcript.json (詳細メタ)
- 認証: 環境変数 AZURE_SPEECH_KEY, AZURE_SPEECH_REGION
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk


def transcribe_file(audio_path: Path, language: str = "ja-JP") -> dict:
    key = os.environ["AZURE_SPEECH_KEY"]
    region = os.environ["AZURE_SPEECH_REGION"]

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_recognition_language = language
    # 詳細出力 (信頼度スコア、n-best) を有効化
    speech_config.output_format = speechsdk.OutputFormat.Detailed
    # プロファニティフィルタを raw に (研究用途、そのまま書き起こし)
    speech_config.set_profanity(speechsdk.ProfanityOption.Raw)

    audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    results: list[dict] = []
    done = False

    def on_recognized(evt):
        r = evt.result
        if r.reason == speechsdk.ResultReason.RecognizedSpeech:
            entry = {
                "text": r.text,
                "offset_sec": r.offset / 1e7,
                "duration_sec": r.duration / 1e7,
            }
            # detailed には JSON 結果が含まれる
            try:
                detail = json.loads(r.json)
                entry["confidence"] = detail.get("NBest", [{}])[0].get("Confidence")
            except Exception:
                pass
            results.append(entry)
            print(f"  [{entry['offset_sec']:6.2f}s] {r.text}")

    def on_session_stopped(evt):
        nonlocal done
        done = True

    def on_canceled(evt):
        nonlocal done
        print(f"[error] canceled: {evt.reason} — {evt.error_details}", file=sys.stderr)
        done = True

    recognizer.recognized.connect(on_recognized)
    recognizer.session_stopped.connect(on_session_stopped)
    recognizer.canceled.connect(on_canceled)

    print(f"[transcribe] starting continuous recognition on {audio_path.name}")
    recognizer.start_continuous_recognition()
    while not done:
        time.sleep(0.5)
    recognizer.stop_continuous_recognition()

    return {
        "audio_file": str(audio_path),
        "language": language,
        "segments": results,
        "full_text": " ".join(r["text"] for r in results),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", type=Path, required=True, help="WAV file (16kHz recommended)")
    ap.add_argument("--language", default="ja-JP")
    args = ap.parse_args()

    load_dotenv()
    if not os.environ.get("AZURE_SPEECH_KEY") or not os.environ.get("AZURE_SPEECH_REGION"):
        sys.exit("[error] AZURE_SPEECH_KEY / AZURE_SPEECH_REGION not set (see .env.example)")

    outputs = Path(__file__).resolve().parent.parent / "outputs"
    outputs.mkdir(exist_ok=True)

    result = transcribe_file(args.audio, language=args.language)
    (outputs / "transcript.txt").write_text(result["full_text"], encoding="utf-8")
    (outputs / "transcript.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[done] {len(result['segments'])} segments → outputs/transcript.txt")


if __name__ == "__main__":
    main()
