"""Quick test to verify Gemini API is working correctly."""
import os, sys
from google import genai

API_KEY = "AIzaSyDA22n27zrJUlfieN6dsGx-SO2wQ0Q0TZQ"  # paste your key here

api_key = API_KEY or os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

test_lines = [
    "[574.21s -> 580.62s]  Paul would say, he said, I exhort my office.\n",
    "[685.55s -> 694.19s]  Tarsus, a city in Caesarea, yet brought up at the feet of Gamaliel.\n",
    "[2030.18s -> 2034.82s]  Uzziah 6.3 says, then shall we know if we follow after to know.\n",
]

prompt = """You are a transcript editor for Salt City Church. Fix transcription errors only.
Known fixes needed:
- "I exhort my office" should be "I magnify my office"
- "Uzziah 6.3" should be "Isaiah 6.3"
Output ONLY the corrected lines, same number as input, no commentary.

""" + "".join(test_lines)

print("Sending test to Gemini...")
response = client.models.generate_content(model="models/gemini-2.0-flash-lite", contents=prompt)
print("\nGemini response:")
print(response.text)
print("\nTest complete.")