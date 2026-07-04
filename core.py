from search import search_web
from fast_ai import ask_ai
from PIL import Image
import pytesseract
import io

import streamlit as st
import google.generativeai as genai

# =========================
# OCR SETUP
# =========================
# (Windows only fallback — safe on Streamlit)
import os

if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =========================
# GEMINI SETUP (STREAMLIT SECRETS FIX)
# =========================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# =========================
# UTIL
# =========================
def limit(text, n):
    if not text:
        return ""
    return text[:n]

def compress_query(query):
    MAX_LEN = 350
    if len(query) <= MAX_LEN:
        return query
    words = query.split()
    return " ".join(words[:40])[:MAX_LEN]

# =========================
# SEARCH FILTER
# =========================
def should_search(query):
    q = query.lower().strip()

    casual = {
        "hi", "hello", "hey", "yo", "sup", "lol",
        "bye", "thanks", "thank you",
        "good morning", "good night", "how are you"
    }
    if q in casual:
        return False

    if len(q.split()) <= 2:
        return False

    math_block = [
        "solve", "simplify", "evaluate", "equation",
        "algebra", "geometry", "probability",
        "mean", "median", "mode",
        "vertex", "slope", "factor",
        "area", "perimeter",
        "shsat", "math", "question", "find", "compute",
        "value of", "expression"
    ]

    if any(word in q for word in math_block):
        return False

    if len(q) > 300:
        return False

    return True

# =========================
# MIME TYPE
# =========================
def get_mime_type(image_bytes):
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    if image_bytes[:4] == b"RIFF":
        return "image/webp"
    return "image/jpeg"

# =========================
# OCR
# =========================
def read_image_ocr(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img)
    except Exception as e:
        print("OCR error:", e)
        return ""

# =========================
# GEMINI VISION (FIXED)
# =========================
def read_image_vision(image_bytes):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = """
Describe ONLY what is visible in the image.
List objects, shapes, text, and layout.
Do NOT guess anything not visible.
"""

        response = model.generate_content([prompt, image_bytes])

        return response.text.strip() if response and response.text else ""

    except Exception as e:
        print("Vision error:", e)
        return ""

# =========================
# MAIN PIPELINE
# =========================
def run(query, image_bytes=None):
    sources = []
    context_parts = []

    vision = ""

    # IMAGE
    if image_bytes:
        vision = read_image_vision(image_bytes)

        if not vision:
            vision = read_image_ocr(image_bytes)

        if vision:
            context_parts.append("IMAGE:\n" + vision[:400])

    # WEB SEARCH
    if should_search(query):
        try:
            safe_query = compress_query(query)
            results = search_web(safe_query)

            for r in results[:3]:
                content = r.get("content", "")
                if content:
                    context_parts.append(content[:250])

                if r.get("url"):
                    sources.append(r["url"])

        except Exception as e:
            print("Search skipped:", e)

    # CONTEXT
    context = "\n\n".join(context_parts).strip()
    if not context:
        context = "No external context provided."

    context = limit(context, 3500)

    # FINAL PROMPT
    if image_bytes:
        final_query = f"""
User question:
{query}

Image info:
{vision[:400]}

Answer clearly and accurately.
"""
    else:
        final_query = query

    final_query = limit(final_query, 2000)

    # AI CALL
    answer = ask_ai(final_query, context)

    return answer, sources