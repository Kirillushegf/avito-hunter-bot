import requests
import re
import time
import os
from flask import Flask
from threading import Thread

TOKEN = "СЮДА_ВСТАВЬ_ТОКЕН"

CITIES = {
    "москва": "moskva",
    "спб": "spb",
    "сочи": "sochi",
    "казань": "kazan",
    "екатеринбург": "ekaterinburg",
    "новосибирск": "novosibirsk",
    "краснодар": "krasnodar",
    "владивосток": "vladivostok"
}

def send_photo(chat_id, photo_url, caption):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        data = {"chat_id": chat_id, "photo": photo_url, "caption": caption, "parse_mode": "HTML"}
        requests.post(url, json=data, timeout=15)
    except:
        pass

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def search_avito(query, city_code):
    url = f"https://www.avito.ru/{city_code}?q={query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Accept-Language": "ru-RU,ru;q=0.8"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        html = r.text
        
        item_ids = re.findall(r'data-item-id="(\d+)"', html)
        if not item_ids:
            item_ids = re.findall(r'itemId-(\d+)', html)
        
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', html)
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html)
        condition_new = re.findall(r'Новый', html)
        photos = re.findall(r'<img[^>]*src="(https://[^"]+\.(jpg|png|jpeg))"', html)
        
        ads = []
        for i in range(min(len(item_ids), 10)):
            price = int(prices[i]) if i < len(prices) else 0
            title = re.sub(r'<[^>]+>', '', titles[i])[:60] if i < len(titles) else "Товар"
            condition = "🆕 Новый" if condition_new else "📦 Б/У"
            photo = photos[i][0] if i < len(photos) else None
            
            ads.append({
                "price": price,
                "url": f"https://www.avito.ru/{city_code}/{item_ids[i]}",
                "title": title,
                "condition": condition,
                "photo": photo
            })
        
        ads.sort(key=lambda x: x["price"])
        return ads[:5]
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def menu_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📖 ШПАРГАЛКА", "callback_data": "help"}],
            [{"text": "🏙️ ГОРОДА", "callback_data": "cities"}]
        ]
    }

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
                    
                    if "callback_query" in upd:
                        cb = upd["callback_query"]
                        chat_id = str(cb["message"]["chat"]["id"])
                        cb_data = cb["data"]
                        
                        if cb_data == "help":
                            help_text = """📖 <b>ШПАРГАЛКА</b>\n\n<b>Как писать запросы:</b>\n<code>диваны москва</code>\n<code>айфон спб</code>\n\n<b>Доступные города:</b>\n""" + "\n".join(CITIES.keys())
                            send(chat_id, help_text)
                        elif cb_data == "cities":
                            cities_text = "🏙️ <b>ГОРОДА</b>\n\n" + "\n".join([f"• {c}" for c in CITIES.keys()])
                            send(chat_id, cities_text)
                        
                        requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={"callback_query_id": cb["id"]})
                    
                    elif "message" in upd:
                        msg = upd["message"]
                        chat_id = str(msg["chat"]["id"])
                        text = msg.get("text", "").strip().lower()
                        
                        if text == "/start":
                            send(chat_id, "🔍 <b>AVITO HUNTER</b>\n\n📸 Фото\n🏷️ Новый/Б/У\n💰 Сортировка по цене\n\n📝 <b>Пример:</b> диваны москва", reply_markup=menu_keyboard())
                        elif text:
                            parts = text.split()
                            query = parts[0]
                            city_name = parts[1] if len(parts) > 1 else "москва"
                            city_code = CITIES.get(city_name)
                            
                            if not city_code:
                                send(chat_id, f"❌ Город '{city_name}' не найден.\nДоступны: {', '.join(CITIES.keys())}")
                                continue
                            
                            send(chat_id, f"🔍 Ищу {query} в {city_name}...")
                            ads = search_avito(query, city_code)
                            
                            if ads:
                                for ad in ads:
                                    caption = f"🏆 {ad['title']}\n💰 {ad['price']:,} ₽\n📋 {ad['condition']}\n🔗 {ad['url']}"
                                    if ad['photo']:
                                        send_photo(chat_id, ad['photo'], caption)
                                    else:
                                        send(chat_id, caption)
                                    time.sleep(0.5)
                            else:
                                send(chat_id, f"❌ Ничего не найдено для {query} в {city_name}")
            time.sleep(0.5)
        except Exception as e:
            print(e)
            time.sleep(5)

app = Flask(__name__)

@app.route('/')
def home():
    return "OK", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    if TOKEN == "СЮДА_ВСТАВЬ_ТОКЕН":
        print("❌ Вставь токен")
    else:
        Thread(target=run_flask).start()
        main()
