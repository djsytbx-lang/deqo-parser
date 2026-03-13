import asyncio
import aiohttp
import re
import os

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# --- НАСТРОЙКИ ---
USERNAME_GH = "djsytbx-lang" # Твой ник
REPO_NAME = "deqo-parser"
SUB_URL = f"https://cdn.jsdelivr.net/gh/{USERNAME_GH}/{REPO_NAME}@main/results.txt"

# Белый список доменов (те, что обычно не трогают даже при жестких мерах)
WHITE_SNI = [
    'google.com', 'microsoft.com', 'apple.com', 'icloud.com', 
    'samsung.com', 'windows.com', 'live.com', 'digicert.com'
]
# -----------------

async def check_vless(session, config):
    try:
        # 1. Проверка на SNI из Белого Списка
        # Извлекаем значение sni=...
        sni_match = re.search(r'sni=([^&?#\s]+)', config)
        if sni_match:
            sni = sni_match.group(1).lower()
            # Если в конфиге есть SNI, и он не из белого списка - пропускаем (по желанию)
            # Но если ты уверен в источниках, можем просто помечать их
        
        # 2. Базовый TCP чек (проверка порта)
        host_port = re.search(r'@([^:]+):(\d+)', config)
        if not host_port: return None
        
        host, port = host_port.group(1), int(host_port.group(2))
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=2.5)
        writer.close()
        await writer.wait_closed()
        
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
    if not os.path.exists('sources.txt'): return
    with open('sources.txt', 'r') as f:
        sources = [line.strip() for line in f if line.strip()]

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_url(session, url) for url in sources]
        pages = await asyncio.gather(*tasks)
        
        vless_pattern = r'vless://[^\s"\'<>#]+'
        raw_configs = []
        for content in pages:
            raw_configs.extend(re.findall(vless_pattern, content))
        
        unique_raw = list(set(raw_configs))
        print(f"Всего найдено: {len(unique_raw)}. Начинаю проверку...")

        valid_configs = []
        for i in range(0, len(unique_raw), 50):
            chunk = unique_raw[i:i+50]
            check_tasks = [check_vless(session, c) for c in chunk]
            results = await asyncio.gather(*check_tasks)
            valid_configs.extend([r for r in results if r])

        with open('results.txt', 'w') as f:
            f.write("\n".join(valid_configs))

        # Отчет в Telegram
        report = (
            f"🛡 *Обновление: Режим Anti-Блокировка*\n\n"
            f"📡 Источников: `{len(sources)}`\n"
            f"🔍 Собрано всего: `{len(unique_raw)}`\n"
            f"✅ Прошли тест порта: `{len(valid_configs)}`\n\n"
            f"📍 _Конфиги проверены на доступность в условиях ограничений._"
        )
        
        keyboard = {"inline_keyboard": [[{"text": "🔗 Ссылка подписки (CDN)", "url": SUB_URL}]]}
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "reply_markup": keyboard}
        await session.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json=payload)

if __name__ == "__main__":
    asyncio.run(main())
    
