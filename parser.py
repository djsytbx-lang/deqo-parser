import asyncio
import aiohttp
import re
import os
import base64

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

async def check_vless(session, config):
    """Простейшая проверка: доступен ли домен из конфига."""
    try:
        # Извлекаем адрес сервера из vless://...@host:port...
        host_port = re.search(r'@([^:]+):(\d+)', config)
        if not host_port:
            return None
        
        host = host_port.group(1)
        # Проверяем только доступность хоста по TCP (быстрый тест)
        conn = asyncio.open_connection(host, host_port.group(2))
        await asyncio.wait_for(conn, timeout=3)
        return config
    except:
        return None

async def fetch_url(session, url):
    try:
        async with session.get(url, timeout=15) as response:
            return await response.text() if response.status == 200 else ""
    except:
        return ""

async def main():
    with open('sources.txt', 'r') as f:
        sources = [line.strip() for line in f if line.strip()]

    async with aiohttp.ClientSession() as session:
        # 1. Сбор данных
        tasks = [fetch_url(session, url) for url in sources]
        pages = await asyncio.gather(*tasks)
        
        vless_pattern = r'vless://[^\s"\'<>#]+'
        raw_configs = []
        for content in pages:
            raw_configs.extend(re.findall(vless_pattern, content))
        
        unique_raw = list(set(raw_configs))
        print(f"Найдено всего: {len(unique_raw)}. Начинаю проверку...")

        # 2. Проверка (Чекер)
        # Чтобы не забанили, проверяем пачками по 50 штук
        valid_configs = []
        for i in range(0, len(unique_raw), 50):
            chunk = unique_raw[i:i+50]
            check_tasks = [check_vless(session, c) for c in chunk]
            results = await asyncio.gather(*check_tasks)
            valid_configs.extend([r for r in results if r])
            print(f"Проверено {min(i+50, len(unique_raw))}...")

        # 3. Сохранение
        with open('results.txt', 'w') as f:
            f.write("\n".join(valid_configs))

        # 4. Отчет
        report = (
            f"🛠 *Парсер с чекером*\n\n"
            f"📡 Источников: `{len(sources)}`\n"
            f"🔍 Всего найдено: `{len(unique_raw)}`\n"
            f"✅ Прошли проверку: `{len(valid_configs)}`"
        )
        
        # Отправка в TG
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown"}
        await session.post(tg_url, json=payload)

if __name__ == "__main__":
    asyncio.run(main())
        
