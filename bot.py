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
    "казань": "kazan",
    "екатеринбург": "ekaterinburg",
    "новосибирск": "novosibirsk",
    "краснодар": "krasnodar",
    "владивосток": "vladivostok"
}

@app.route('/')
def home():
    return "OK", 200

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def search_avito(query, city):
    url = f"https://www.avito.ru/{city}?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        ids = re.findall(r'itemId-(\d+)', r.text)
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', r.text)
        titles = re.findall(r'<h3[^>]*>(.*?)</h3>', r.text)
        
        ads = []
        for i in range(min(len(ids), 5)):
            price = int(prices[i]) if i < len(prices) else 0
            title = re.sub(r'<[^>]+>', '', titles[i])[:50] if i < len(titles) else "Товар"
            ads.append({
                "title": title,
                "price": price,
                "url": f"https://www.avito.ru/{city}/{ids[i]}"
            })
        ads.sort(key=lambda x: x["price"])
        return ads
    except:
        return []

def main():
    last_id = 0
    print("✅ Бот запущен!")
    
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{TOKEN}/getUpdates", params={"offset": last_id + 1, "timeout": 30}, timeout=35)
            data = r.json()
            
            if data.get("ok"):
                for upd in data["result"]:
                    last_id = upd["update_id"] + 1
                    msg = upd.get("message")
                    if msg:
                        chat_id = msg["chat"]["id"]
                        text = msg.get("text", "").strip().lower()
                        
                        # Обработка команд
                        if text == "/start":
                            description = """
🔍 <b>AVITO HUNTER</b> — бот для поиска выгодных предложений на Авито

<b>📌 КАК ЭТО РАБОТАЕТ:</b>
1️⃣ Ты пишешь <b>товар и город</b>
2️⃣ Бот ищет объявления на Авито
3️⃣ Сортирует по цене (от дешёвых к дорогим)
4️⃣ Присылает ссылки на лучшие варианты

<b>📝 ПРИМЕРЫ ЗАПРОСОВ:</b>
• <code>диваны москва</code>
• <code>айфон спб</code>
• <code>машина казань</code>
• <code>стиральная машина</code>

<b>🏙️ ДОСТУПНЫЕ ГОРОДА:</b>
""" + ", ".join(CITIES.keys()) + """

<b>💡 СОВЕТЫ:</b>
• Пиши товар на русском
• Город можно не указывать (по умолчанию Москва)
• Чем точнее запрос, тем лучше результат

<b>📞 ПРОБЛЕМЫ?</b>
Просто напиши /start
"""
                            send(chat_id, description)
                        
                        elif text.startswith("/"):
                            pass
                        
                        # Обработка поискового запроса
                        elif text:
                            parts = text.split()
                            query = parts[0]
                            city_name = parts[1] if len(parts) > 1 and parts[1] in CITIES else "москва"
                            city_code = CITIES.get(city_name, "moskva")
                            
                            send(chat_id, f"🔍 Ищу <b>{query}</b> в <b>{city_name}</b>...")
                            ads = search_avito(query, city_code)
                            
                            if ads:
                                result = f"🏆 <b>САМЫЕ ВЫГОДНЫЕ {query.upper()}</b>\n\n"
                                for i, ad in enumerate(ads, 1):
                                    price_text = f"{ad['price']:,} ₽" if ad['price'] > 0 else "Цена не указана"
                                    result += f"{i}. <b>{ad['title'][:40]}</b>\n"
                                    result += f"   💰 {price_text}\n"
                                    result += f"   🔗 {ad['url']}\n\n"
                                send(chat_id, result)
                            else:
                                send(chat_id, f"❌ Ничего не найдено для <b>{query}</b> в <b>{city_name}</b>\n\nПопробуй другой запрос или город.")
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
