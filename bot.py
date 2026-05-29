import requests
import re
import time
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)
TOKEN = os.environ.get("BOT_TOKEN")

CITIES = {
    "москва": "moskva",
    "спб": "spb",
    "сочи": "sochi"
}

@app.route('/')
def home():
    return "OK", 200

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except:
        pass

def search_avito(query, city):
    url = f"https://www.avito.ru/{city}?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        ids = re.findall(r'itemId-(\d+)', r.text)
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', r.text)
        ads = []
        for i in range(min(len(ids), 5)):
            price = int(prices[i]) if i < len(prices) else 0
            ads.append(f"💰 {price} ₽\nhttps://www.avito.ru/{city}/{ids[i]}")
        return ads
    except:
        return []

def main():
    last = 0
    print("✅ Бот запущен")
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last + 1, "timeout": 25})
            data = r.json()
            if data.get("ok"):
                for upd in data["result"]:
                    last = upd["update_id"] + 1
                    msg = upd.get("message")
                    if msg:
                        chat = msg["chat"]["id"]
                        text = msg.get("text", "").strip().lower()
                        if text == "/start":
                            send(chat, "🔍 Напиши: диваны москва")
                        elif text:
                            parts = text.split()
                            q = parts[0]
                            c = parts[1] if len(parts) > 1 else "moskva"
                            send(chat, f"🔍 Ищу {q}...")
                            ads = search_avito(q, c)
                            if ads:
                                for ad in ads:
                                    send(chat, ad)
                                    time.sleep(0.3)
                            else:
                                send(chat, "❌ Ничего нет")
            time.sleep(0.5)
        except:
            time.sleep(5)

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Ошибка: нет токена")
    else:
        Thread(target=run).start()
        main()
