import asyncio
import aiohttp
import re
import os

# Данные из секретов GitHub
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- НАСТРОЙКИ ---
USERNAME = "djsytl"  
REPO_NAME = "deqo-parser"
SUB_URL = f"https://cdn.jsdelivr.net/gh/djsytbx/deqo-parser@main/results.txt"
# -----------------

async def check_vless(session, config):
    """Проверяет доступность сервера по TCP."""
    try:
        host_port = re.search(r'@([^:]+):(\d+)', config)
        if not host_port:
            return None
        
        host = host_port.group(1)
        port = int(host_port.group(2))
        
        # Попытка открыть соединение (тайм-аут 3 секунды)
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=3.0)
        writer.close()
        await writer.wait_closed()
        return config
    except:
        return None

async def fetch_url(session, url):
    """Загружает содержимое страницы."""
    try:
        async with session.get(url, timeout=15) as response:
            return await response.text() if response.status == 200 else ""
    except:
        return ""

async def main():
    # Читаем источники из файла
    if not os.path.exists('sources.txt'):
        print("Файл sources.txt не найден!")
        return

    with open('sources.txt', 'r') as f:
        sources = [line.strip() for line in f if line.strip()]

    async with aiohttp.ClientSession() as session:
        # 1. Сбор сырых ссылок
        tasks = [fetch_url(session, url) for url in sources]
        pages = await asyncio.gather(*tasks)
        
        vless_pattern = r'vless://[^\s"\'<>#]+'
        raw_configs = []
        for content in pages:
            raw_configs.extend(re.findall(vless_pattern, content))
        
        unique_raw = list(set(raw_configs))
        print(f"Найдено уникальных: {len(unique_raw)}. Начинаю чекер...")

        # 2. Чекер (проверка пачками по 50 штук)
        valid_configs = []
        for i in range(0, len(unique_raw), 50):
            chunk = unique_raw[i:i+50]
            check_tasks = [check_vless(session, c) for c in chunk]
            results = await asyncio.gather(*check_tasks)
            valid_configs.extend([r for r in results if r])
            print(f"Проверено: {min(i+50, len(unique_raw))}/{len(unique_raw)}")

        # 3. Сохранение результата в файл
        with open('results.txt', 'w') as f:
            f.write("\n".join(valid_configs))

        # 4. Отправка отчета в Telegram с кнопкой
        report = (
            f"🛠 *База обновлена и проверена*\n\n"
            f"📡 Источников опрошено: `{len(sources)}`\n"
            f"🔍 Всего найдено: `{len(unique_raw)}`\n"
            f"✅ Рабочих конфигов: `{len(valid_configs)}`\n\n"
            f"🚀 _Используй кнопку ниже для импорта в Hiddify/v2rayNG:_"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "🔗 Скопировать ссылку подписки", "url": SUB_URL}
            ]]
        }
        
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": report, 
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        
        async with session.post(tg_url, json=payload) as resp:
            if resp.status == 200:
                print("Отчет успешно отправлен в Telegram")
            else:
                print(f"Ошибка отправки в TG: {resp.status}")

if __name__ == "__main__":
    asyncio.run(main())
    
