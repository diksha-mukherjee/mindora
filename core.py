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

    # 1. casual chat → NO search
    casual = {
        "hi", "hello", "hey", "yo", "sup", "lol",
        "bye", "thanks", "thank you",
        "good morning", "good night", "how are you"
    }
    if q in casual:
        return False

    # 2. too short → NO search
    if len(q.split()) <= 2:
        return False

    # 3. math / school / SHSAT → NO search
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

    # 4. general noise filter
    if len(q) > 300:
        return False

    # 5. default → allow search only for real-world questions
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
        mime_type = get_mime_type(image_bytes)

        prompt = (
            "Describe ONLY what is visible in the image.\n"
            "List objects, shapes, text, and layout.\n"
            "Do NOT guess anything not visible."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=mime_type
                )
            ]
        )

        # FIX: safer response handling
        if response and getattr(response, "text", None):
            return response.text.strip()

        return ""

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

    # =========================
    # IMAGE PIPELINE (FIXED LOGIC)
    # =========================
    if image_bytes is not None and len(image_bytes) > 0:
        print("IMAGE RECEIVED ✔")

        vision = read_image_vision(image_bytes)

        if not vision:
            vision = read_image_ocr(image_bytes)

        if vision:
            context_parts.append("IMAGE:\n" + vision[:400])
    else:
        print("NO IMAGE RECEIVED ❌")

    # =========================
    # WEB SEARCH
    # =========================
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

    # =========================
    # BUILD CONTEXT
    # =========================
    context = "\n\n".join(context_parts).strip()

    if not context:
        context = "No external context provided."

    context = limit(context, 3500)

    # =========================
    # FINAL QUERY
    # =========================
    if image_bytes:
        final_query = f"""
User question:
{query}

Image info:
{vision[:400]}

Rules:
- Use image info if present
- Be accurate
- Do NOT hallucinate

Answer:
"""
    else:
        final_query = query

    final_query = limit(final_query, 2000)

    # =========================
    # AI CALL
    # =========================
    answer = ask_ai(final_query, context)

    return answer, sources