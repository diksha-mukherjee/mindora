import os
from dotenv import load_dotenv

load_dotenv()

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def ask_ai(question, context=""):
    # ---------------------
    # HARD SAFETY LIMITS
    # ---------------------
    question = question[-2000:]
    context = context[-3500:]

    # ---------------------
    # SMART PROMPT
    # ---------------------
    prompt = f"""
You are a helpful AI assistant.

RULES:
- Be clear and natural
- Do not over-explain unless needed
- Use context only if relevant
- Ignore noise in context

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    # ---------------------
    # API CALL
    # ---------------------
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content