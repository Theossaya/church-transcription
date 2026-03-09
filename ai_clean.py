"""
ai_clean.py  —  Stage 3 of the Salt City Church transcription pipeline
Powered by Groq (free tier — https://console.groq.com)

Usage:
    python ai_clean.py <corrected_transcript.txt> [sermon topic]

Examples:
    python ai_clean.py fruitful_christianity_1_transcript_corrected.txt
    python ai_clean.py fruitful_christianity_1_transcript_corrected.txt "Fruitful Christianity - Seven Pillars"

Setup:
    1. Go to https://console.groq.com and sign up free (no credit card)
    2. Click API Keys -> Create API Key
    3. Paste your key into API_KEY below
    4. Run: pip install groq
"""

import sys
import os
import time
from groq import Groq

# ── Configuration ──────────────────────────────────────────────────────────────

API_KEY    = ""              # Paste your free Groq API key here
MODEL      = "llama-3.3-70b-versatile"
CHUNK_SIZE = 100             # Lines per API call — conservative for token limits
OVERLAP    = 5               # Lines of overlap between chunks

# ── Prompt ─────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a precise transcript editor for Salt City Church, a Nigerian Pentecostal church.

Your job is to fix transcription errors in sermon transcripts produced by Whisper (a speech-to-text model).
The transcripts already have some corrections applied. Your task is to catch what remains.

CHURCH CONTEXT:
- Church: Salt City Church (never "South City Church")
- Pastor: Tobore David
- Series: Fruitful Christianity, based on 2 Peter 1:1-11
- The seven pillars of fruitfulness: Virtue/Power, Knowledge, Temperance, Patience, Godliness, Brotherly Kindness, Charity/Love

KEY PEOPLE:
- Rev. Sam Obadan — Pastor Tobore's mentor
- Daddy G.O. — General Overseer (Nigerian church title)
- Papa Irosh — a minister quoted by the pastor

KEY THEOLOGICAL TERMS:
- ARGOUS (Greek) — useless, unproductive, out of service
- AKARPOUS (Greek) — unfruitful
- Hupako / Kupako — Greek for possession/having
- Pleonasa — Greek for abounding
- Imago Dei — image and likeness of God

KNOWN CORRECT PHRASES (never change these):
- "brotherly kindness" — never "bodily kindness"
- "I magnify my office" — never "I exhort my office"
- "Daddy G.O." — never "Daddy Gio"
- "Salt City Church" — never "South City Church"
- "this will bring you insight" — opening line of every sermon

WHAT TO FIX:
- Misheard Bible book names (e.g. "Uzziah 6:3" should be "Isaiah 6:3")
- "March 28" or "March in 28" should be "Matthew 28"
- Misheard biblical names (e.g. "Buchenheiser" should be "Nebuchadnezzar")
- "Barnabas and saw to the work" should be "Barnabas and Saul to the work"
- "near God water" should be "near Golgotha"
- Garbled sentences where the meaning is clear from context
- Greek or Hebrew terms that have been misheard
- Words phonetically similar but clearly wrong in context

WHAT NOT TO CHANGE:
- The pastor's informal Nigerian speech patterns — these are intentional
- Pidgin English phrases — do not correct to standard English
- Congregation responses and interactive moments
- Timestamps — preserve every timestamp exactly as written e.g. [000.00s -> 000.00s]
- Anything you are uncertain about — leave it exactly as-is

CRITICAL RULES:
1. Output the SAME number of lines as the input. Never merge or split lines.
2. Preserve every timestamp character-for-character.
3. Only change the spoken text after the timestamp, and only when you are confident.
4. Output only the cleaned transcript lines. No commentary, headers, explanations, or markdown.
5. When in doubt, leave it alone. A wrong correction is worse than a missed one."""

# ── Functions ──────────────────────────────────────────────────────────────────

def read_transcript(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()

def write_transcript(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def clean_chunk(client, lines, chunk_num, total_chunks, sermon_topic=""):
    topic_line = f"SERMON TOPIC: {sermon_topic}\n\n" if sermon_topic else ""
    user_message = (
        f"{topic_line}"
        f"Clean the following transcript chunk ({chunk_num}/{total_chunks}). "
        f"Fix transcription errors only. Preserve all timestamps and line count exactly. "
        f"Output ONLY the transcript lines, nothing else.\n\n"
        + "".join(lines)
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        temperature=0.1,   # low temperature = more conservative/predictable edits
        max_tokens=4096,
    )

    result_text  = response.choices[0].message.content
    result_lines = result_text.splitlines(keepends=True)

    # Ensure trailing newline if input had one
    if lines and lines[-1].endswith("\n") and result_lines and not result_lines[-1].endswith("\n"):
        result_lines[-1] += "\n"

    return result_lines

def process_transcript(input_path, sermon_topic=""):
    api_key = API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ERROR: No API key found.")
        print("Paste your Groq key into API_KEY at the top of this script.")
        print("Get a free key at: https://console.groq.com")
        sys.exit(1)

    client = Groq(api_key=api_key)

    print(f"\nReading: {input_path}")
    all_lines   = read_transcript(input_path)
    total_lines = len(all_lines)
    print(f"Total lines: {total_lines}")

    output_path = input_path.replace(".txt", "_ai_cleaned.txt")

    # Build chunks with overlap
    chunks = []
    start  = 0
    while start < total_lines:
        end = min(start + CHUNK_SIZE, total_lines)
        chunks.append((start, end))
        if end == total_lines:
            break
        start = end - OVERLAP

    total_chunks = len(chunks)
    print(f"Processing {total_chunks} chunks of ~{CHUNK_SIZE} lines...")
    print(f"Saving to: {output_path}\n")

    all_cleaned = []

    for i, (start, end) in enumerate(chunks, 1):
        chunk_lines = all_lines[start:end]
        print(f"  Chunk {i}/{total_chunks} (lines {start+1}-{end})...", end=" ", flush=True)

        try:
            cleaned = clean_chunk(client, chunk_lines, i, total_chunks, sermon_topic)
            if i == 1:
                all_cleaned.extend(cleaned)
            else:
                all_cleaned.extend(cleaned[OVERLAP:])
            print(f"done")
            if i < total_chunks:
                time.sleep(1)   # gentle rate limiting

        except Exception as e:
            print(f"\nERROR: {e}")
            print("Keeping original lines for this chunk.")
            if i == 1:
                all_cleaned.extend(chunk_lines)
            else:
                all_cleaned.extend(chunk_lines[OVERLAP:])
            time.sleep(5)

    write_transcript(output_path, all_cleaned)
    print(f"\nDone! Saved to: {output_path}")
    print(f"Lines in: {total_lines} | Lines out: {len(all_cleaned)}")
    if abs(total_lines - len(all_cleaned)) > 5:
        print("WARNING: Line count changed significantly. Please check the output.")

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_clean.py <transcript_file.txt> [sermon topic]")
        sys.exit(1)

    input_file = sys.argv[1]
    topic      = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    process_transcript(input_file, topic)