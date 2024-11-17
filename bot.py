from telebot.async_telebot import AsyncTeleBot
import feedparser
import asyncio
import json
import os, re

from config import *

JSON_FILE = 'last_guid.json'  # Шлях до файлу для збереження останньої новини

# Ініціалізація асинхронного бота
bot = AsyncTeleBot(BOT_TOKEN)

# Функція для зчитування останнього збереженого GUID з JSON
def read_last_guid():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as file:
            data = json.load(file)
            return data.get("last_guid", None)
    return None

# Функція для збереження останнього GUID у JSON
def save_last_guid(last_guid):
    with open(JSON_FILE, 'w') as file:
        json.dump({"last_guid": last_guid}, file)

# Функція для очищення HTML
def clean_html(text):
    # Видаляємо всі HTML теги
    text = re.sub(r'<.*?>', '', text)
    
    # Заміна спеціальних символів
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')
    text = text.replace('&rsquo;', "'").replace('&hellip;', '…').replace('&nbsp;', ' ')  # Додаткові символи

    # Форматуємо текст (наприклад, робимо абзаци через нові рядки)
    text = text.replace('\n', ' ').replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
    
    # Заміна стилів та інших HTML елементів, які не підтримує Telegram API
    text = re.sub(r'<.*?>', '', text)  # Ще раз видалимо теги, що могли залишитись
    
    return text.strip()

async def fetch_latest_news():
    """Функція перевіряє RSS і відправляє новини в чат, якщо є нові."""
    last_guid = read_last_guid()  # Читання останнього GUID з файлу
    feed = feedparser.parse(RSS_URL)

    # Якщо є новини
    if feed.entries:
        entry = feed.entries[0]
        if last_guid != entry.id:
            # Оновлюємо останню новину
            save_last_guid(entry.id)

            title = entry.title
            pub_date = entry.published
            link = entry.link
            description = entry.get("full-text", "").strip()

            # Очищаємо опис від HTML-тегів
            cleaned_description = clean_html(description)

            # Перевірка на наявність картинки в <enclosure>
            image_url = None
            if 'enclosures' in entry:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('file'):
                        image_url = enclosure.get('url')
                        break

            MAX_CAPTION_LENGTH = 1024
            # Формуємо текст повідомлення без картинок
            message = (
                f"*{title}*\n\n"
                f"{pub_date}\n\n"
                f"{cleaned_description}\n\n"
                f"— Джерело ({link})"
            )
            
            # Якщо весь текст повідомлення перевищує ліміт, обрізаємо опис
            if len(message) > MAX_CAPTION_LENGTH:
                # Обрізаємо лише частину опису, залишаючи місце для джерела
                max_description_length = MAX_CAPTION_LENGTH - len(f"*{title}*\n\n{pub_date}\n\n— Джерело ({link})") - 3
                cleaned_description = cleaned_description[:max_description_length] + '...'
                
                # Оновлюємо повідомлення з обрізаним описом
                message = (
                    f"*{title}*\n\n"
                    f"{pub_date}\n\n"
                    f"{cleaned_description}\n\n"
                    f"— Джерело ({link})"
                )
            
            # Якщо є зображення
            if image_url:
                # Надсилаємо зображення разом з текстовим підписом
                await bot.send_photo(CHAT_ID, image_url, caption=message, parse_mode='Markdown')
            else:
                # Якщо картинки немає, відправимо тільки текст
                await bot.send_message(CHAT_ID, message, parse_mode='Markdown', disable_web_page_preview=True)


#Перевірка на парсинг RSS сторінки. В кращому випадку видалити цю частину коду після налаштувань.
@bot.message_handler(commamds=['test'])
async def test(message):
    await fetch_latest_news()

async def main():
    """Запуск регулярної перевірки RSS з інтервалом у 5 хвилин."""
    while True:
        try:
            print('Перевірка новин...')
            await fetch_latest_news()
        except Exception as e:
            print(f"Помилка при отриманні новин: {e}")
        await asyncio.sleep(check_rss_timeout)

async def start_bot():
    """Запускає бота в асинхронному режимі."""
    await bot.polling(non_stop=True)

# Запуск бота та перевірки новин
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Запускаємо обидва завдання в циклі подій
    loop.create_task(start_bot())  # Запуск бота
    loop.create_task(main())  # Запуск перевірки новин
    loop.run_forever()  # Чекаємо на завершення задач
