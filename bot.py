import requests
import re
import time
import os
from flask import Flask
from threading import Thread

TOKEN = "8911252420:AAGZ2DrDreC8qSOr7Lyr5Azph60bU4GcHR0"

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

def send(chat_id, text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

def search_avito(query, city_code):
    url = f"https://www.avito.ru/{city_code}?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        ids = re.findall(r'itemId-(\d+)', r.text)
        prices = re.findall(r'<span[^>]*itemprop="price"[^>]*content="(\d+)"', r.text)
        
        ads = []
        for i in range(min(len(ids), 15)):
            price = int(prices[i]) if i < len(prices) else 0
            ads.append({
                "price": price,
                "url": f"https://www.avito.ru/{city_code}/{ids[i]}"
            })
        ads.sort(key=lambda x: x["price"])
        return ads[:5]
    except:
        return []

def main():
    last_id = 0
    print("✅ Бот запущен!")
    
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
                            send(chat_id, "🔍 <b>Avito Hunter</b>\n\nНапиши: <b>диваны москва</b>\n<b>айфон спб</b>\n\n🏆 Самые дешёвые — первыми!")
                        
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
                                msg = f"🏆 <b>САМЫЕ ВЫГОДНЫЕ {query.upper()} В {city_name.upper()}</b>\n\n"
                                for i, ad in enumerate(ads, 1):
                                    price = f"{ad['price']:,} ₽" if ad['price'] > 0 else "Цена не указана"
                                    msg += f"{i}. 💰 <b>{price}</b>\n🔗 {ad['url']}\n\n"
                                send(chat_id, msg)
                            else:
                                send(chat_id, f"❌ Ничего не найдено для <b>{query}</b> в <b>{city_name}</b>")
            time.sleep(0.5)
        except:
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
        Thread(target=run_flask).start()
        main()