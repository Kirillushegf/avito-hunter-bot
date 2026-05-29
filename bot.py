import requests
import re
import time
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)
TOKEN = os.environ.get("BOT_TOKEN")

CITIES = {
    "🇷🇺 Москва": "moskva",
    "🇷🇺 СПБ": "spb",
    "🇷🇺 Сочи": "sochi",
    "🇷🇺 Адлер": "adler",
    "🇷🇺 Дагомыс": "dagomys",
    "🇷🇺 Лоо": "loo",
    "🇷🇺 Вардане": "vardane",
    "🇷🇺 Краснодар": "krasnodar",
    "🇷🇺 Киров": "kirov",
    "🇷🇺 Луза": "luza",
    "🇷🇺 Казань": "kazan",
    "🇷🇺 Екатеринбург": "ekaterinburg"
}

@app.route('/')
def home():
    return "OK", 200

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=5)
    except:
        pass

def search_avito(query, city_code):
    url = f"https://www.avito.ru/{city_code}?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=6)
        ids = re.findall(r'itemId-(\d+)', r.text)
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', r.text)
        
        ads = []
        for i in range(min(len(ids), 4)):
            price = int(prices[i]) if i < len(prices) else 0
            ads.append({
                "price": price,
                "url": f"https://www.avito.ru/{city_code}/{ids[i]}"
            })
        ads.sort(key=lambda x: x["price"])
        return ads
    except:
        return []

def city_keyboard():
    buttons = []
    row = []
    for name, code in CITIES.items():
        row.append({"text": name, "callback_data": f"city_{code}"})
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return {"inline_keyboard": buttons}

def main():
    last_id = 0
    user_queries = {}
    print("✅ Быстрый бот запущен!")
    
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_id + 1, "timeout": 25}, timeout=30)
            data = r.json()
            
            if data.get("ok"):
                for upd in data["result"]:
                    last_id = upd["update_id"] + 1
                    
                    if "callback_query" in upd:
                        cb = upd["callback_query"]
                        chat_id = str(cb["message"]["chat"]["id"])
                        cb_data = cb["data"]
                        
                        if cb_data.startswith("city_"):
                            city_code = cb_data.replace("city_", "")
                            city_name = next((k for k, v in CITIES.items() if v == city_code), city_code)
                            query = user_queries.get(chat_id, "")
                            
                            if query:
                                send(chat_id, f"🔍 Ищу <b>{query}</b> в <b>{city_name}</b>...")
                                ads = search_avito(query, city_code)
                                
                                if ads:
                                    msg = f"🏆 <b>САМЫЕ ВЫГОДНЫЕ {query.upper()}</b>\n\n"
                                    for i, ad in enumerate(ads, 1):
                                        price = f"{ad['price']:,} ₽" if ad['price'] > 0 else "Цена не указана"
                                        msg += f"{i}. 💰 {price}\n🔗 {ad['url']}\n\n"
                                    send(chat_id, msg)
                                else:
                                    send(chat_id, f"❌ Ничего не найдено для <b>{query}</b> в <b>{city_name}</b>")
                            else:
                                send(chat_id, "❌ Сначала напишите, что искать")
                        
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"]})
                    
                    elif "message" in upd:
                        msg = upd["message"]
                        chat_id = str(msg["chat"]["id"])
                        text = msg.get("text", "").strip()
                        
                        if text == "/start":
                            desc = f"🔍 <b>AVITO HUNTER</b> (быстрая версия)\n\n<b>Как работает:</b>\n1️⃣ Напиши товар\n2️⃣ Выбери город\n3️⃣ Получи ссылки\n\n<b>Примеры:</b>\nдиваны, iphone, машина\n\n🏙️ <b>Города ({len(CITIES)}):</b> {', '.join(list(CITIES.keys())[:6])} и др."
                            send(chat_id, desc)
                        
                        elif text:
                            user_queries[chat_id] = text
                            send(chat_id, "📍 <b>Выберите город:</b>", reply_markup=city_keyboard())
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
