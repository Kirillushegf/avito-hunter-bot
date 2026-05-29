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
    "сочи": "sochi",
    "краснодар": "krasnodar",
    "киров": "kirov",
    "казань": "kazan",
    "екатеринбург": "ekaterinburg"
}

@app.route('/')
def home():
    return "OK", 200

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=5)
    except:
        pass

def search_avito(query, city_code):
    url = f"https://www.avito.ru/{city_code}?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        ids = re.findall(r'itemId-(\d+)', r.text)
        links = [f"https://www.avito.ru/{city_code}/{x}" for x in ids[:5]]
        return links
    except:
        return []

def main():
    last_id = 0
    print("✅ Бот запущен")
    
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_id + 1, "timeout": 25}, timeout=30)
            data = r.json()
            
            if data.get("ok"):
                for upd in data["result"]:
                    last_id = upd["update_id"] + 1
                    msg = upd.get("message")
                    if msg:
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip().lower()
                        
                        if text == "/start":
                            send(chat_id, "🔍 <b>Avito Hunter</b>\n\nНапиши товар и город:\n<b>диваны москва</b>\n<b>айфон спб</b>\n\nДоступные города: " + ", ".join(CITIES.keys()))
                        
                        elif text:
                            parts = text.split()
                            if len(parts) < 1:
                                send(chat_id, "❌ Напиши: диваны москва")
                                continue
                            
                            query = parts[0]
                            city = parts[1] if len(parts) > 1 and parts[1] in CITIES else "moskva"
                            city_code = CITIES.get(city, "moskva")
                            
                            send(chat_id, f"🔍 Ищу {query}...")
                            links = search_avito(query, city_code)
                            
                            if links:
                                msg = f"🏆 {query.upper()}\n\n"
                                for i, link in enumerate(links, 1):
                                    msg += f"{i}. {link}\n"
                                send(chat_id, msg)
                            else:
                                send(chat_id, f"❌ Ничего не найдено для {query}")
            time.sleep(0.5)
        except:
            time.sleep(5)

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Нет токена")
    else:
        Thread(target=run).start()
        main()
