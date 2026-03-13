import asyncio
import aiohttp
import re
import os

# Константы (используем GitHub Secrets)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def fetch_url(session, url):
    """Скачивает содержимое страницы."""
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                return await response.text()
            return ""
    except Exception as e:
        print(f"Ошибка при запросе к {url}: {e}")
        return ""

async def send_telegram_report(message):
    """Отправляет отчет в твой Telegram-канал."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram секреты не настроены. Пропускаю отправку.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json=payload)
        except Exception as e:
            print(f"Не удалось отправить сообщение в TG: {e}")

async def main():
    # 1. Читаем список источников
    try:
        with open('sources.txt', 'r') as f:
            sources = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print("Файл sources.txt не найден!")
        return

    # 2. Собираем данные со всех ссылок одновременно
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in sources]
        results = await asyncio.gather(*tasks)

    # 3. Извлекаем VLESS ссылки через регулярное выражение
    # Паттерн ищет vless:// и всё до пробела или кавычки
    vless_pattern = r'vless://[^\s"\'<>#]+'
    all_configs = []
    
    for content in results:
        found = re.findall(vless_pattern, content)
        all_configs.extend(found)

    # 4. Удаляем дубликаты
    unique_configs = sorted(list(set(all_configs)))

    # 5. Сохраняем результат в файл
    with open('results.txt', 'w') as f:
        f.write("\n".join(unique_configs))

    # 6. Отправляем уведомление
    report = (
        f"🔄 *Обновление парсера*\n\n"
        f"📡 Источников опрошено: `{len(sources)}`\n"
        f"✅ Найдено уникальных VLESS: `{len(unique_configs)}`"
    )
    await send_telegram_report(report)
    print(f"Готово. Собрано {len(unique_configs)} конфигов.")

if __name__ == "__main__":
    asyncio.run(main())
