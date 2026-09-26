import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

# Short, punchy, realistic 8-slide pitch script tailored for Claude Community Stockholm
SLIDES = [
    (
        1,
        "Welcome to Claude Community Stockholm! I'm the AI clone of Akkireddy Challa. Meet PitchRoast: the satirical AI venture committee that roasts your startup in 15 seconds."
    ),
    (
        2,
        "Investors always lie with polite rejections like 'Let's stay in touch.' In reality, your unit economics are broken. PitchRoast gives you the honest truth instantly."
    ),
    (
        3,
        "Four AI judges debate in parallel: Max Market attacks fake demand; Penny Pinch audits your burn; Tech Toby exposes duct-tape code; and Boss Shark decides Deal or No Deal."
    ),
    (
        4,
        "We tested real Swedish ideas: Klarna for Regret, splitting 3 AM shame into four payments; and FikaSync, locking your IDE if you skip your afternoon cinnamon bun!"
    ),
    (
        5,
        "Two doors, one engine: The Founder Hot Seat gives you a clean boardroom; the Syndicate Observatory gives operators Phoenix tracing, token telemetry, and PIN security."
    ),
    (
        6,
        "Our parallel fan-out architecture cuts latency by 68 percent using Claude Opus and Fable, backed by zero-crash offline resilience."
    ),
    (
        7,
        "Quantitative risk scores, hilarious covenants, and a genuine one percent pivot to real revenue. PitchRoast turns polite lies into constructive delight."
    ),
    (
        8,
        "Now it's your turn! Shout out your startup idea from the audience, and let our four AI judges roast you live on screen in 15 seconds!"
    ),
]

repo_root = Path(__file__).resolve().parent.parent
audio_dir = repo_root / "audio"
docs_audio_dir = repo_root / "docs" / "audio"

for d in [audio_dir, docs_audio_dir]:
    d.mkdir(parents=True, exist_ok=True)


def generate_with_elevenlabs(api_key: str, voice_id: str = "JBFqnCBsd6RMkjVDRZzb"):
    """Generate audio using ElevenLabs API (Voice: George / Adam / custom)."""
    print("🎙️ Generating hyper-realistic audio using ElevenLabs API...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    for slide_num, text in SLIDES:
        print(f"Generating ElevenLabs audio for Slide {slide_num}...")
        mp3_path = audio_dir / f"slide{slide_num}.mp3"
        m4a_path = audio_dir / f"slide{slide_num}.m4a"
        wav_path = audio_dir / f"slide{slide_num}.wav"

        headers = {
            "xi-api-key": api_key.strip(),
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
            },
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req) as response, open(mp3_path, "wb") as f:
                f.write(response.read())

            # Convert mp3 to m4a (aac) and wav
            subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(mp3_path), str(m4a_path)], check=True)
            subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(mp3_path), str(wav_path)], check=True)

            # Copy to docs/audio
            subprocess.run(["cp", str(m4a_path), str(docs_audio_dir / f"slide{slide_num}.m4a")], check=True)
            subprocess.run(["cp", str(wav_path), str(docs_audio_dir / f"slide{slide_num}.wav")], check=True)

            if mp3_path.exists():
                os.remove(mp3_path)
            print(f"  ✅ Slide {slide_num} generated with ElevenLabs")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"  ❌ ElevenLabs HTTP {e.code} error: {err_body}")
            print("  Falling back to macOS TTS for remaining slides...")
            generate_with_macos()
            return


def generate_with_macos(voice: str = "Daniel"):
    """Generate audio using macOS built-in speech synthesizer."""
    print(f"🔊 Generating audio using macOS speech synthesizer ({voice})...")
    for slide_num, text in SLIDES:
        print(f"Generating audio for Slide {slide_num}...")
        aiff_path = audio_dir / f"slide{slide_num}.aiff"
        m4a_path = audio_dir / f"slide{slide_num}.m4a"
        wav_path = audio_dir / f"slide{slide_num}.wav"

        # 1. Generate AIFF with say (macOS)
        subprocess.run(["say", "-v", voice, "-r", "175", text, "-o", str(aiff_path)], check=True)

        # 2. Convert to m4a (aac)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff_path), str(m4a_path)], check=True)

        # 3. Convert to wav (universal)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(aiff_path), str(wav_path)], check=True)

        # Copy to docs/audio as well
        subprocess.run(["cp", str(m4a_path), str(docs_audio_dir / f"slide{slide_num}.m4a")], check=True)
        subprocess.run(["cp", str(wav_path), str(docs_audio_dir / f"slide{slide_num}.wav")], check=True)

        if aiff_path.exists():
            os.remove(aiff_path)
        print(f"  ✅ Slide {slide_num} generated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PitchRoast narration audio tracks")
    parser.add_argument("--api-key", help="ElevenLabs API Key (optional)")
    parser.add_argument("--voice-id", default="JBFqnCBsd6RMkjVDRZzb", help="ElevenLabs Voice ID")
    parser.add_argument("--macos-voice", default="Daniel", help="macOS voice (default: Daniel)")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("ELEVENLABS_API_KEY") or os.getenv("XI_API_KEY")
    if api_key:
        generate_with_elevenlabs(api_key, args.voice_id)
    else:
        generate_with_macos(args.macos_voice)

    print("All audio files generated and synced successfully!")
