from telebot.async_telebot import AsyncTeleBot
import feedparser
import asyncio
import json
import os, re
from datetime import datetime

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
    text = re.sub(r'<.*?>', '', text)
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')
    text = text.replace('&rsquo;', "'").replace('&hellip;', '…').replace('&nbsp;', ' ')
    text = text.replace('&ndash;', '—').replace('&mdash;', '—')
    text = text.replace('&laquo;', '«').replace('&raquo;', '»') 
    text = text.replace('\n', ' ').replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
    text = re.sub(r'<.*?>', '', text)
    return text.strip()

async def fetch_and_send_news():
    """Функція перевіряє RSS і надсилає новини."""
    last_guid = read_last_guid()
    feed = feedparser.parse(RSS_URL)
    new_entries = []

    # Якщо файл відсутній, беремо лише останню новину
    if not last_guid:
        if feed.entries:
            new_entries = [feed.entries[0]]
            save_last_guid(feed.entries[0].id)
    else:
        for entry in feed.entries:
            if entry.id == last_guid:
                break
            new_entries.append(entry)

    new_entries.reverse()  # Щоб новини надсилалися у хронологічному порядку

    for entry in new_entries:
        title = entry.title
        pub_date = entry.published
        link = entry.link
        description = entry.get("full-text", "").strip()
        cleaned_description = clean_html(description)
        image_url = None

        # Перевірка на наявність картинки
        if 'enclosures' in entry:
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('file'):
                    image_url = enclosure.get('url')
                    break

        MAX_CAPTION_LENGTH = 1024
        message = (
            f"*{title}*\n\n"
            f"{pub_date}\n\n"
            f"{cleaned_description}\n\n"
            f"— Джерело ({link})"
        )

        # Обрізка довгих повідомлень
        if len(message) > MAX_CAPTION_LENGTH:
            max_description_length = MAX_CAPTION_LENGTH - len(f"*{title}*\n\n{pub_date}\n\n— Джерело ({link})") - 3
            cleaned_description = cleaned_description[:max_description_length] + '...'
            message = (
                f"*{title}*\n\n"
                f"{pub_date}\n\n"
                f"{cleaned_description}\n\n"
                f"— Джерело ({link})"
            )

        # Надсилання повідомлення
        if image_url:
            await bot.send_photo(CHAT_ID, image_url, caption=message, parse_mode='Markdown')
        else:
            await bot.send_message(CHAT_ID, message, parse_mode='Markdown', disable_web_page_preview=True)

        # Зберігаємо останній GUID
        save_last_guid(entry.id)
        await asyncio.sleep(send_news_interval)

async def main():
    """Запуск регулярної перевірки RSS з інтервалом у 5 хвилин."""
    while True:
        try:
            print('Перевірка новин...')
            await fetch_and_send_news()
        except Exception as e:
            print(f"Помилка при отриманні новин: {e}")
        await asyncio.sleep(check_rss_timeout)

async def start_bot():
    """Запускає бота в асинхронному режимі."""
    await bot.polling(non_stop=True)

# Запуск бота та перевірки новин
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())  # Запуск бота
    loop.create_task(main())  # Запуск перевірки новин
    loop.run_forever()  # Чекаємо на завершення задач