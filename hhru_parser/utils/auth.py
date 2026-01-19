import requests
import aiohttp
import asyncio

def validate_cookies_sync(cookies: dict) -> bool:
    if not cookies or "hhtoken" not in cookies:
        return False
    
    url = "https://hh.ru/settings"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, cookies=cookies, headers=headers, allow_redirects=True, timeout=10)
        return resp.status_code == 200 and "login" not in resp.url.lower()
    except Exception:
        return False

async def validate_cookies_async(cookies: dict) -> bool:
    if not cookies or "hhtoken" not in cookies:
        return False
    
    url = "https://hh.ru/settings"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    try:
        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as resp:
                return resp.status == 200 and "login" not in str(resp.url).lower()
    except Exception:
        return False
