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
    "🇷🇺 Санкт-Петербург": "spb",
    "🇷🇺 Сочи": "sochi",
    "🇷🇺 Адлер": "adler",
    "🇷🇺 Дагомыс": "dagomys",
    "🇷🇺 Лоо": "loo",
    "🇷🇺 Вардане": "vardane",
    "🇷🇺 Краснодар": "krasnodar",
    "🇷🇺 Киров": "kirov",
    "🇷🇺 Луза": "luza",
    "🇷🇺 Казань": "kazan",
    "🇷🇺 Екатеринбург": "ekaterinburg",
    "🇷🇺 Новосибирск": "novosibirsk",
    "🇷🇺 Владивосток": "vladivostok"
}

@app.route('/')
def home():
    return "OK", 200

def send(chat_id, text, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            data["reply_markup"] = reply_markup
        requests.post(url, json=data, timeout=10)
    except:
        pass

def send_photo(chat_id, photo_url, caption):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
        requests.post(url, json=data, timeout=15)
    except:
        pass

def search_avito(query, city_code):
    url = f"https://www.avito.ru/{city_code}?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html",
        "Accept-Language": "ru-RU,ru;q=0.8,en;q=0.5"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        html = r.text
        
        ids = re.findall(r'itemId-(\d+)', html)
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', html)
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html)
        condition_new = re.findall(r'Новый', html)
        photos = re.findall(r'<img[^>]*src="(https://[^"]+\.(jpg|png|jpeg))"', html)
        
        ads = []
        for i in range(min(len(ids), 10)):
            price = int(prices[i]) if i < len(prices) else 0
            title = re.sub(r'<[^>]+>', '', titles[i])[:60] if i < len(titles) else "Товар"
            condition = "🆕 Новый" if i < len(condition_new) else "📦 Б/У"
            photo = photos[i][0] if i < len(photos) else None
            
            ads.append({
                "price": price,
                "url": f"https://www.avito.ru/{city_code}/{ids[i]}",
                "title": title,
                "condition": condition,
                "photo": photo
            })
        
        ads.sort(key=lambda x: x["price"])
        return ads[:5]
    except Exception as e:
        print(f"Ошибка: {e}")
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
    user_cities = {}
    user_queries = {}
    print("✅ Бот запущен!")
    
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_id + 1, "timeout": 30}, timeout=35)
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
                            user_cities[chat_id] = city_code
                            query = user_queries.get(chat_id, "")
                            
                            if query:
                                send(chat_id, f"🔍 Ищу <b>{query}</b> в <b>{city_name}</b>...")
                                ads = search_avito(query, city_code)
                                
                                if ads:
                                    for ad in ads:
                                        caption = f"🏆 <b>{ad['title']}</b>\n💰 {ad['price']:,} ₽\n📋 {ad['condition']}\n🔗 <a href='{ad['url']}'>Открыть</a>"
                                        if ad['photo']:
                                            send_photo(chat_id, ad['photo'], caption)
                                        else:
                                            send(chat_id, caption)
                                        time.sleep(0.5)
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
                            cities_list = "\n".join(list(CITIES.keys())[:8] + ["..."] + list(CITIES.keys())[-4:])
                            description = f"""
🔍 <b>AVITO HUNTER</b>

<b>🌍 Поддерживаются языки:</b>
🇷🇺 Русский
🇬🇧 Английский (iPhone, Samsung, Xiaomi)

<b>📝 КАК РАБОТАЕТ:</b>
1️⃣ Напишите <b>название товара</b> (любым языком)
2️⃣ Выберите <b>город</b>
3️⃣ Получите <b>самые выгодные предложения</b>

<b>📌 ПРИМЕРЫ:</b>
• <code>диваны</code> или <code>sofa</code>
• <code>iphone 13</code>
• <code>стиральная машина</code>
• <code>Samsung TV</code>

<b>🏙️ Доступные города ({len(CITIES)}):</b>
{cities_list}
"""
                            send(chat_id, description)
                        
                        elif text.startswith("/"):
                            pass
                        
                        elif text:
                            user_queries[chat_id] = text
                            send(chat_id, "📍 <b>Выберите город:</b>", reply_markup=city_keyboard())
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Ошибка: нет токена. Добавь BOT_TOKEN на Render")
    else:
        Thread(target=run).start()
        main()
