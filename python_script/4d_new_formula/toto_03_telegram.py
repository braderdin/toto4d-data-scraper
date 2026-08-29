import os
import requests
from dotenv import load_dotenv

# Muat turun persekitaran dari .env.local jika wujud (Local execution)
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env.local")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text_message):
    if not BOT_TOKEN or not CHAT_ID:
        print("[-] Ralat: TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID tidak dijumpai.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text_message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if res_data.get("ok"):
            print("[+] Mesej berjaya dihantar ke Telegram!")
            return True
        else:
            print(f"[-] Telegram API Error: {res_data}")
    except Exception as e:
        print(f"[-] Ralat semasa menghantar ke Telegram: {e}")
    
    return False

if __name__ == "__main__":
    send_telegram_message("🤖 Test Notifikasi dari Toto 4D Scraper!")