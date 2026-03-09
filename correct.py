import json
import re
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
CORRECTIONS_FILE = "corrections.json"
# ─────────────────────────────────────────────────────────────────────────────

def load_corrections():
    """Load corrections dictionary, create default one if it doesn't exist."""
    if not Path(CORRECTIONS_FILE).exists():
        default = {
            "_comment": "Add corrections as 'wrong text': 'right text'. Case-insensitive matching.",
            "_comment2": "Longer phrases first — they take priority over shorter ones.",

            "Tobare Debits": "Tobore David",
            "Tobore Debits": "Tobore David",
            "South City Church": "Salt City Church",
            "Salt city church": "Salt City Church",
            "MySaltCity": "MySaltCity",

            "hair to the throne": "heir to the throne",
            "the hair,": "the heir,",
            "the hair ": "the heir ",
            "you are the hair": "you are the heir",
            "as the hair": "as the heir",

            "Some 107 and a vest": "Psalm 107 verse 2",
            "samiest twins": "same in spirit",

            "innocent": "in essence",
            "Innocent": "In essence"
        }
        with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        print(f"Created default {CORRECTIONS_FILE} — edit it to add your own corrections.")

    with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Strip comment keys
    return {k: v for k, v in data.items() if not k.startswith("_comment")}


def apply_corrections(text, corrections):
    """Apply all corrections to text. Longer phrases matched first."""
    sorted_corrections = sorted(corrections.items(), key=lambda x: len(x[0]), reverse=True)
    
    for wrong, right in sorted_corrections:
        # Case-insensitive replacement that preserves surrounding text
        pattern = re.compile(re.escape(wrong), re.IGNORECASE)
        
        def replace_match(match):
            matched = match.group(0)
            # Preserve capitalisation if first letter was capital
            if matched[0].isupper() and right[0].islower():
                return right[0].upper() + right[1:]
            return right
        
        text = pattern.sub(replace_match, text)
    
    return text


def process_file(input_path):
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    corrections = load_corrections()
    print(f"Loaded {len(corrections)} corrections from {CORRECTIONS_FILE}")

    with open(input_path, "r", encoding="utf-8") as f:
        original = f.read()

    corrected = apply_corrections(original, corrections)

    # Save corrected version with _corrected suffix
    output_path = input_path.parent / (input_path.stem + "_corrected.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(corrected)

    # Report what changed
    original_lines = original.splitlines()
    corrected_lines = corrected.splitlines()
    
    changes = 0
    print("\n── Changes made ─────────────────────────────────────────────")
    for i, (orig, corr) in enumerate(zip(original_lines, corrected_lines)):
        if orig != corr:
            changes += 1
            print(f"  Line {i+1}:")
            print(f"    BEFORE: {orig.strip()}")
            print(f"    AFTER:  {corr.strip()}")
    
    if changes == 0:
        print("  No corrections applied — transcript may already be clean.")
    
    print(f"\nDone. {changes} line(s) corrected.")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python correct.py <transcript_file.txt>")
        print("Example: python correct.py fruitful_christianity_1_transcript.txt")
        sys.exit(1)
    
    process_file(sys.argv[1])