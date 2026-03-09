# Salt City Church — Automated Sermon Transcription Pipeline

An end-to-end speech-to-text pipeline built for Nigerian Pentecostal church audio. Converts MP3 sermon recordings into accurate text transcripts with timestamps, using a three-stage architecture specifically designed around the error profile of Nigerian Pentecostal speech.

**Current pipeline accuracy: 91–93%**  
**Designed next step: Claude API cleaning → projected 95–97%**

---

## The Problem

Salt City Church produces weekly sermon recordings averaging 90 minutes. These are published to a public Telegram channel but exist only as audio — the teaching content is inaccessible to search, reference, or repurpose without manual listening.

Generic speech-to-text services achieve 75–85% accuracy on this content because they have never encountered:
- Nigerian Pentecostal speech patterns and code-switching (English ↔ Pidgin)
- Domain-specific theological vocabulary
- Proper names: Nigerian pastors, biblical figures, Greek/Hebrew teaching terms

Manual transcription takes 4–6 hours per sermon. This pipeline runs unattended overnight and produces a corrected transcript by morning.

---

## Pipeline Architecture

```
MP3 Audio
    │
    ▼
┌────────────────────────────────────────┐
│  Stage 1: transcribe.py               │
│  Whisper large-v2 + VAD filtering     │
│  Accuracy: ~88%   Time: 2–3 hrs       │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  Stage 2: correct.py                  │
│  Domain-specific corrections dict     │
│  Accuracy: 91–93%  Time: 2 seconds    │
└────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────┐
│  Stage 3: ai_clean.py  [DESIGNED]     │
│  LLM contextual post-processing       │
│  Projected: 95–97%  Time: 3–4 min     │
│  Requires: Claude API key + $5 credit │
└────────────────────────────────────────┘
    │
    ▼
Final Transcript with Timestamps
```

---

## Accuracy Benchmark

| Stage | Accuracy | Processing Time | Cost |
|---|---|---|---|
| Whisper large-v2 (raw) | 82–88% | 2–3 hours | Free |
| + VAD filtering | 84–90% | 2–3 hours | Free |
| + Corrections dictionary | 91–93% | +2 seconds | Free |
| + Claude API *(designed)* | ~95–97% | +3–4 minutes | ~$0.05–0.15/sermon |

Accuracy measured against manually prepared reference transcripts across 3 sermons. Lower bound applies to heavy Pidgin and congregation-response sections; upper bound applies to structured teaching segments.

---

## Why This Is Hard

Standard STT models fail on this corpus for several compounding reasons:

**Nigerian speech patterns** — The pastor code-switches between formal English and Pidgin mid-sentence. Prosody (pace, pitch, emphasis) differs significantly from the predominantly American/British English in Whisper's training data.

**Domain vocabulary** — Greek theological terms (`ARGOUS`, `AKARPOUS`, `HUPAKO`), Nigerian pastor titles (`Daddy G.O.`), and church-specific phrases (`Salt City Church`, `brotherly kindness`) have no equivalent in standard training data. Whisper confidently misheard these the same way every time.

**Proper names** — `Tobore David` → `Tobore Debbins`. `Rev. Sam Obadan` → `Reverend Sam Obama`. `Nebuchadnezzar` → `Buchenheiser`. High-confidence wrong answers that cannot be fixed by prompt engineering — only post-processing works.

**Congregation interaction** — Call-and-response, background voices, and overlapping speech during informal sections produce chaotic output from any VAD-naive approach.

---

## Technical Approach

### Stage 1 — Whisper Inference

Uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), a CTranslate2-optimised implementation of OpenAI Whisper. Key configuration decisions:

```python
model = WhisperModel("large-v2", device="cpu", compute_type="int8")

segments, info = model.transcribe(
    audio_path,
    language="en",       # Lock to English — prevents mid-transcript language switching
    beam_size=5,         # Optimal accuracy/speed tradeoff
    vad_filter=True,     # Silero VAD — filters silence and noise
    vad_parameters=dict(
        min_silence_duration_ms=500,  # Preserve natural speech rhythm
        speech_pad_ms=400             # Prevent clipping of word edges
    )
)
```

**Model selection:** `large-v2` (1.5B parameters) was chosen after testing `small`, `medium`, and `large-v2` against reference transcripts. Accuracy improvement from `medium` to `large-v2` was ~6 percentage points — significant enough to justify the 3× processing time increase.

**VAD filtering:** Without VAD, Whisper produces hallucinated text during silence and congregation noise. Silero VAD preprocessing reduced these artefacts substantially and improved structured-segment accuracy by ~2–4%.

**Language lock:** Without `language="en"`, Whisper occasionally switches to Yoruba or Igbo when Nigerian words appear, producing garbled output for several seconds. Locking to English prevents this.

**Output format:**
```
[000.34s → 006.74s]  Hi there, this is Tobore David and here is the teaching ministry of Salt City Church.
[006.74s → 012.45s]  This will bring you insight, show you proof of the power of God,
```

---

### Stage 2 — Corrections Dictionary

A JSON key-value map of systematic Whisper errors to their correct forms. Built iteratively by comparing raw output against 3 manually verified reference transcripts.

**Key finding:** The dictionary converges fast. Sermon 1 required 14 entries. Sermon 2 added 8. Sermon 3 added ~5. By sermon 4–5 the dictionary is largely stable — maintenance cost approaches zero.

**Why this works where prompt engineering doesn't:** Whisper is not uncertain about its wrong answers — it is confidently wrong. No amount of configuration changes what it outputs for `brotherly kindness` → `bodily kindness`. Only post-inference string replacement fixes it.

Selected entries from `corrections.json`:

```json
{
  "South City Church":  "Salt City Church",
  "bodily kindness":    "brotherly kindness",
  "near God water":     "near Golgotha",
  "Buchenheiser":       "Nebuchadnezzar",
  "Tobore Debbins":     "Tobore David",
  "Reverend Sam Obama": "Rev. Sam Obadan",
  "Uzziah 6.3":         "Isaiah 6.3",
  "Daddy Gio":          "Daddy G.O.",
  "quitters":           "akarpous"
}
```

---

### Stage 3 — LLM Contextual Cleaning *(Designed, Not Deployed)*

The 7–9% error rate remaining after Stage 2 consists of *contextual* errors — corrections that require understanding what is being said. A dictionary cannot solve these. An LLM can.

The script (`ai_clean.py`) is written and tested. It passes the corrected transcript to an LLM in 100-line chunks with a detailed system prompt containing:
- Church identity and series context
- Key people referenced
- Greek/Hebrew teaching terms in use
- Explicit examples of known error patterns
- Strict instructions to leave uncertain passages unchanged

**Provider evaluation:**

| Provider | Model | Result |
|---|---|---|
| Anthropic Claude | claude-sonnet-4-5 | Optimal — not deployed (cost preference during dev) |
| Google Gemini | gemini-1.5-flash | Geographic restriction — free tier unavailable in Nigeria |
| Groq | llama-3.3-70b | Functional but hallucinates ~10 changes/sermon alongside ~25 correct fixes |

**To activate Stage 3:** Add an Anthropic API key to `ai_clean.py`. Estimated cost $0.05–0.15 per sermon.

---

## Project Structure

```
church-transcription/
│
├── transcribe.py          # Stage 1: Whisper transcription
├── correct.py             # Stage 2: Dictionary post-processing  
├── ai_clean.py            # Stage 3: LLM contextual cleaning
├── corrections.json       # Systematic error corrections dictionary
│
├── requirements.txt       # Python dependencies
├── README.md
└── .gitignore
```

---

## Setup

**Requirements:** Python 3.9+, 8GB RAM minimum (16GB recommended), 4GB disk space for model

```bash
# Clone the repository
git clone https://github.com/yourusername/church-transcription.git
cd church-transcription

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# First run downloads Whisper large-v2 model (~3GB) automatically
```

---

## Usage

```bash
# Stage 1 — Transcribe (2–3 hours, leave overnight)
python transcribe.py path/to/sermon.mp3

# Stage 2 — Apply corrections dictionary (2 seconds)
python correct.py path/to/sermon_transcript.txt

# Stage 3 — LLM cleaning (optional, requires API key)
python ai_clean.py path/to/sermon_transcript_corrected.txt "Sermon Topic"
```

---

## Extending the Corrections Dictionary

When a recurring error is identified in a delivered transcript, add it to `corrections.json`:

```json
{
  "wrong transcription": "correct text"
}
```

Corrections are case-sensitive. Add both capitalised and lowercase variants if the word appears in both forms. The correction applies to all future sermons automatically.

---

## Known Limitations

- **Pidgin accuracy:** Heavy Pidgin sections achieve ~78–83% accuracy — the irreducible floor without fine-tuning on Pidgin-English data
- **Congregation responses:** Overlapping voices during call-and-response reduce accuracy in those segments
- **Novel proper nouns:** New speakers or new series introduce new proper noun errors not yet in the dictionary — typically 2–5 new entries per new series
- **Processing speed:** 2–3 hours per sermon on CPU. Acceptable for overnight unattended use; not suitable for real-time or same-day delivery

---

## Future Work

- **Stage 3 deployment** — Claude API activation for contextual cleaning (immediate, ~$5)
- **Archive processing** — Bulk transcription of 900+ archived sermons via Telegram API download + cloud GPU batch processing (~$30–75 one-time)
- **Searchable archive** — Web interface for keyword/scripture/series search across full archive
- **Automated weekly brief** — Auto-generate pull quotes, key points, and scripture references on each new sermon upload
- **Fine-tuning** — With 30+ hours of transcribed Salt City audio, Whisper fine-tuning could address the Pidgin accuracy gap at the model level

---

## Environment

Developed and tested on:
- Windows 11, Intel i7-11370H, 16GB RAM (CPU inference)
- Python 3.10, faster-whisper 0.10.x, Whisper large-v2

---

## Church Context

Built for **Salt City Church**, Warri, Nigeria. Pastor: Tobore David.  
Telegram channel: [SaltCity Central](https://t.me/mysaltcity) — 1,098 subscribers
