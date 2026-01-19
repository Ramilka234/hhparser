import time
import asyncio
import sys
from pathlib import Path

# Add project root to path with high priority
sys.path.insert(0, str(Path(__file__).parent.parent))

from hhru_parser.methods import HTTP_Parser, AsyncHTTPParser
import inspect

print(f"DEBUG: HTTP_Parser file: {inspect.getfile(HTTP_Parser)}")
print(f"DEBUG: AsyncHTTPParser file: {inspect.getfile(AsyncHTTPParser)}")

async def benchmark():
    query = "Python"
    limit = 40
    page = 0
    user_cookies = {} 
    
    total_requests = 1 + limit

    print(f"=== Benchmark: {query} (page {page}, limit {limit}, total {total_requests} requests) ===\n")

    print("Running Synchronous Parser...")
    start_sync = time.time()
    sync_parser = HTTP_Parser(query, limit, page=page, cookies=user_cookies)
    try:
        sync_results = sync_parser.search()
        end_sync = time.time()
        sync_duration = end_sync - start_sync
        sync_rps = total_requests / sync_duration
        print(f"Sync Results: {len(sync_results)} vacancies found")
        print(f"Sync Total Time: {sync_duration:.2f}s")
        print(f"Sync RPS: {sync_rps:.2f}")
    except Exception as e:
        print(f"Sync failed: {e}")
        sync_duration = 0
        sync_rps = 0

    print("\n" + "-"*30 + "\n")

    print("Running Asynchronous Parser...")
    start_async = time.time()
    async_parser = AsyncHTTPParser(query, limit, page=page, cookies=user_cookies)
    try:
        async_results = await async_parser.search()
        end_async = time.time()
        async_duration = end_async - start_async
        async_rps = total_requests / async_duration
        print(f"Async Results: {len(async_results)} vacancies found")
        print(f"Async Total Time: {async_duration:.2f}s")
        print(f"Async RPS: {async_rps:.2f}")
    except Exception as e:
        print(f"Async failed: {e}")
        async_duration = 0
        async_rps = 0

    print("\n" + "="*40)
    if async_rps > 0 and sync_rps > 0:
        improvement = (async_rps / sync_rps)
        print(f"🚀 Async is {improvement:.2f}x faster than Sync")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(benchmark())
