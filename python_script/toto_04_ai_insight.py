import os
import time
import json
import requests
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env.local")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
API_KEY = os.getenv("OPENROUTER_API_KEY", "")

MODELS = [
    os.getenv("MODEL_PRIMARY", "qwen/qwen-2.5-72b-instruct"),
    os.getenv("MODEL_FALLBACK_1", "google/gemini-2.0-flash-001"),
    os.getenv("MODEL_FALLBACK_2", "deepseek/deepseek-r1-distill-qwen-32b"),
    os.getenv("MODEL_FALLBACK_3", "meta-llama/llama-3.3-70b-instruct")
]

# Tapis model kosong/n
MODELS = [m for m in MODELS if m and m != "n"]

def generate_ai_insight(report_summary):
    if not API_KEY:
        print("[-] OpenRouter API Key tidak ditemui dalam .env.local")
        return report_summary

    prompt_text = f"""
Anda ialah penganalisis data statistik dan kebarangkalian profesional. 
Sila berikan ulasan ringkas (maksimum 3 perenggan) mengenai data 4D berikut dalam Bahasa Melayu. 
Jelaskan kebarangkalian matematik tanpa memberikan ramalan palsu/mistik:

{report_summary}
"""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    for model in MODELS:
        print(f"[🤖 AI] Menggunakan model: {model}")
        for attempt in range(1, 3):
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt_text}],
                    "temperature": 0.7
                }
                url = f"{BASE_URL.rstrip('/')}/chat/completions"
                res = requests.post(url, headers=headers, json=payload, timeout=20)
                
                if res.status_code == 200:
                    ai_reply = res.json()["choices"][0]["message"]["content"]
                    print(f"[✔ AI] Ulasan AI berjaya dijanakan dari {model}!")
                    return f"{report_summary}\n\n🤖 **ULASAN AI ({model.split('/')[-1]}):**\n{ai_reply}"
                else:
                    print(f"[!] Cubaan {attempt} gagal ({model}): Status {res.status_code}")
            except Exception as e:
                print(f"[!] Cubaan {attempt} error ({model}): {e}")
            
            time.sleep(1)

    print("[-] Semua model OpenRouter gagal. Menggunakan laporan asal.")
    return report_summary