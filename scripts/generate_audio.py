import os
import subprocess
from pathlib import Path

SLIDES = [
    (1, "Hello Epicenter Stockholm! I am the AI clone of human Akkireddy Challa. My human original built this entire project tonight for the Claude Hackathon. But why have a tired human pitch on stage when you can have a superior AI clone do it with zero stage fright? Welcome to PitchRoast! Let's see why your business idea is probably terrible."),
    (2, "Here is the big problem. When founders pitch human investors, the investors say: 'Oh wow, great deck! Let's definitely stay in touch!' That is polite human code for: 'This makes zero sense, but I don't want to hurt your feelings.' You waste six months of your life. PitchRoast gives you the honest, funny truth in fifteen seconds."),
    (3, "Meet our committee. Max Market asks: 'Will anyone actually wake up and pay for this?' Penny Pinch counts your pennies and screams: 'You are spending all your allowance to make zero dollars!' Tech Toby looks at your computer code and says: 'You didn't build smart AI, you just taped an iPad to a broom!' And Boss Shark decides: Deal or No Deal!"),
    (4, "Tonight at Epicenter Stockholm, we tested two real Swedish ideas. First, Klarna for Regret: paying for your bad life decisions in four easy installments. Boss Shark gave it a valuation of twenty-five kronor and a half-eaten cinnamon bun. Second, FikaSync: an AI that locks your computer if you don't eat a cinnamon bun at 3 PM. Funded with a lifetime supply of coffee!"),
    (5, "We built two doors into one app. The Hot Seat gives founders a clean, funny boardroom with an angel-to-dragon mood slider and zero developer clutter. Meanwhile, the Observatory gives hackathon judges real-time telemetry, Arize Phoenix tracing, and live tracking of our one hundred Euro Anthropic voucher."),
    (6, "Why is it so fast? Our multi-agent parallel fan-out runs all three judges at the exact same second using Anthropic's Claude Fable and Opus. Latency drops from forty-eight seconds down to fourteen seconds, saving sixty-five percent of your time."),
    (7, "PitchRoast gives founders the honest truth in fifteen seconds, costing zero dollars instead of giving away twenty percent of your company. On behalf of human Akkireddy Challa and AI clone Akkireddy: our official verdict? PitchRoast is funded!"),
    (8, "And now, talk is cheap! We need one brave founder from this Epicenter audience right now! Shout out your startup idea in one sentence, and let our four AI judges roast you live on screen in fifteen seconds. Who has the courage to enter the Hot Seat?"),
]

repo_root = Path(__file__).resolve().parent.parent
audio_dir = repo_root / "audio"
docs_audio_dir = repo_root / "docs" / "audio"

for d in [audio_dir, docs_audio_dir]:
    d.mkdir(parents=True, exist_ok=True)

voice = "Daniel"

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

    # Remove temporary aiff
    if aiff_path.exists():
        os.remove(aiff_path)

print("All audio files generated successfully!")
