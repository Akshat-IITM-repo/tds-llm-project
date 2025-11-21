import httpx
import asyncio

async def solve_quiz(payload):
    url = payload["url"]
    print(f"Received quiz URL: {url}")
    # Placeholder – real logic added later
    await asyncio.sleep(1)
    print("Solver ready.")

