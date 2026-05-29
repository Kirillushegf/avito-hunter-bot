import requests
import re
import time
import json
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
    "владивосток": "vladivostok",
    "киров": "kirov",
    "ростов": "rostov"
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'utf-8'
        html = r.text
        
        # Полный разбор страницы
        item_ids = re.findall(r'data-item-id="(\d+)"', html)
        if not item_ids:
            item_ids = re.findall(r'/item_(\d+)', html)
        if not item_ids:
            item_ids = re.findall(r'itemId-(\d+)', html)
        
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', html)
        titles = re.findall(r'<h3[^>]*itemprop="name"[^>]*>(.*?)</h3>', html)
        if not titles:
            titles = re.findall(r'<a[^>]*itemprop="url"[^>]*><span>(.*?)</span></a>', html)
        if not titles:
            titles = re.findall(r'<h3[^>]*>(.*?)</h3>', html)
        
        is_new = re.findall(r'Новый', html)
        photos = re.findall(r'<img[^>]*src="(https://[^"]+\.(jpg|png|jpeg))"', html)
        
        ads = []
        for i in range(min(len(item_ids), 10)):
            price = int(prices[i]) if i < len(prices) else 0
            title = re.sub(r'<[^>]+>', '', titles[i])[:70] if i < len(titles) else "Товар"
            condition = "🆕 Новый" if is_new else "📦 Б/У"
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
        print(f"Ошибка парсинга: {e}")
        return []

def main():
    last_id = 0
    print("✅ Бот запущен! Ищу на Авито...")
    
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
                            send(chat_id, "🔍 <b>Avito Hunter</b>\n\n📸 Фото объявлений\n🏷️ Состояние (новое/б/у)\n💰 Сортировка по цене\n\n📝 <b>Примеры:</b>\nдиваны москва\nайфон спб\nмашина казань")
                        
                        elif text.startswith("/"):
                            pass
                        
                        else:
                            parts = text.split()
                            if len(parts) < 1:
                                send(chat_id, "❌ Напиши: диваны москва")
                                continue
                            
                            query = parts[0]
                            city_name = parts[1] if len(parts) > 1 else "москва"
                            city_code = CITIES.get(city_name)
                            
                            if not city_code:
                                cities_list = ", ".join(CITIES.keys())
                                send(chat_id, f"❌ Город '{city_name}' не найден.\nДоступны: {cities_list}")
                                continue
                            
                            send(chat_id, f"🔍 Ищу <b>{query}</b> в <b>{city_name}</b>...")
                            ads = search_avito(query, city_code)
                            
                            if ads:
                                for i, ad in enumerate(ads, 1):
                                    price_text = f"{ad['price']:,} ₽" if ad['price'] > 0 else "Цена не указана"
                                    caption = f"🏆 <b>{ad['title']}</b>\n\n💰 <b>{price_text}</b>\n📋 {ad['condition']}\n🔗 <a href='{ad['url']}'>Открыть объявление</a>"
                                    
                                    if ad['photo']:
                                        send_photo(chat_id, ad['photo'], caption)
                                    else:
                                        send(chat_id, caption)
                                    time.sleep(0.5)
                            else:
                                send(chat_id, f"❌ Ничего не найдено для <b>{query}</b> в <b>{city_name}</b>\nПопробуй другой запрос или город.")
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка: {e}")
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
        print("❌ Вставь свой токен в код!")
    else:
        print("🔥 Avito Hunter запущен!")
        Thread(target=run_flask).start()
        main()
