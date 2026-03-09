import sys
import time
from faster_whisper import WhisperModel

# ── Config ────────────────────────────────────────────────────────────────────
MODEL_SIZE = "large-v2"
AUDIO_FILE   = sys.argv[1] if len(sys.argv) > 1 else "sermon.mp3"
OUTPUT_FILE  = AUDIO_FILE.rsplit(".", 1)[0] + "_transcript.txt"

INITIAL_PROMPT = (
    "This is a Christian church sermon. The speaker is a Nigerian pastor. "
    "Common words include: Holy Spirit, anointing, grace, hallelujah, "
    "salvation, righteousness, covenant, glory, dominion, mandate."
)
# ─────────────────────────────────────────────────────────────────────────────

print(f"Loading model: {MODEL_SIZE} (first run will download ~3GB, be patient)...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

print(f"Transcribing: {AUDIO_FILE}")
print("This will take a while — go make tea.\n")

start = time.time()

segments, info = model.transcribe(
    AUDIO_FILE,
    language="en",
    initial_prompt=INITIAL_PROMPT,
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for segment in segments:
        timestamp = f"[{segment.start:06.2f}s → {segment.end:06.2f}s]"
        line = f"{timestamp}  {segment.text.strip()}"
        print(line)
        f.write(line + "\n")

elapsed = time.time() - start
print(f"\nDone. Transcript saved to: {OUTPUT_FILE}")
print(f"Time taken: {elapsed/60:.1f} minutes")