import subprocess
import os

SLIDES = [
    (1, "Hello Epicenter Stockholm! I am the AI clone of human Akkireddy Challa. My human original built this entire project tonight for the Claude Hackathon. But why have a tired human pitch on stage when you can have a superior AI clone do it with zero stage fright? Welcome to PitchRoast! Let's see why your business idea is probably terrible."),
    (2, "Here is the big problem. When founders pitch human investors, the investors say: 'Oh wow, great deck! Let's definitely stay in touch!' That is polite human code for: 'This makes zero sense, but I don't want to hurt your feelings.' You waste six months of your life. PitchRoast gives you the honest, funny truth in fifteen seconds."),
    (3, "Meet our committee. Max Market asks: 'Will anyone actually wake up and pay for this?' Penny Pinch counts your pennies and screams: 'You are spending all your allowance to make zero dollars!' Tech Toby looks at your computer code and says: 'You didn't build smart AI, you just taped an iPad to a broom!' And Boss Shark decides: Deal or No Deal!"),
    (4, "Tonight at Epicenter Stockholm, we tested two real Swedish ideas. First, Klarna for Regret: paying for your bad life decisions in four easy installments. Boss Shark gave it a valuation of twenty-five kronor and a half-eaten cinnamon bun. Second, FikaSync: an AI that locks your computer if you don't eat a cinnamon bun at 3 PM. Funded with a lifetime supply of coffee!"),
    (5, "We built two doors into one app. The Hot Seat gives founders a clean, funny boardroom with an angel-to-dragon mood slider and zero developer clutter. Meanwhile, the Observatory gives hackathon judges real-time telemetry, Arize Phoenix tracing, and live tracking of our one hundred Euro Anthropic voucher."),
    (6, "Why is it so fast? Our multi-agent parallel fan-out runs all three judges at the exact same second using Anthropic's Claude Fable and Opus. Latency drops from forty-eight seconds down to fourteen seconds, saving sixty-five percent of your time."),
    (7, "PitchRoast gives founders the honest truth in fifteen seconds, costing zero dollars instead of giving away twenty percent of your company. On behalf of human Akkireddy Challa and AI clone Akkireddy: our official verdict? PitchRoast is funded. Thank you, Stockholm!")
]

out_dirs = [
    "/Users/aue729/AIEXP/pitchroast/docs/audio",
    "/Users/aue729/AIEXP/pitchroast/audio"
]

for d in out_dirs:
    os.makedirs(d, exist_ok=True)

voice = "Daniel"

for slide_num, text in SLIDES:
    print(f"Generating audio for Slide {slide_num}...")
    aiff_path = f"/Users/aue729/AIEXP/pitchroast/docs/audio/slide{slide_num}.aiff"
    m4a_path = f"/Users/aue729/AIEXP/pitchroast/docs/audio/slide{slide_num}.m4a"
    wav_path = f"/Users/aue729/AIEXP/pitchroast/docs/audio/slide{slide_num}.wav"
    
    # 1. Generate AIFF with say
    subprocess.run(["say", "-v", voice, "-r", "175", text, "-o", aiff_path], check=True)
    
    # 2. Convert to m4a (aac)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", aiff_path, m4a_path], check=True)
    
    # 3. Convert to wav (universal)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", aiff_path, wav_path], check=True)
    
    # Also copy to root audio/
    subprocess.run(["cp", m4a_path, f"/Users/aue729/AIEXP/pitchroast/audio/slide{slide_num}.m4a"], check=True)
    subprocess.run(["cp", wav_path, f"/Users/aue729/AIEXP/pitchroast/audio/slide{slide_num}.wav"], check=True)
    
    # Remove temporary aiff
    if os.path.exists(aiff_path):
        os.remove(aiff_path)

print("All audio files generated successfully!")
