
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
import asyncio
from .solver import solve_quiz

app = FastAPI()

SECRET = "CHANGE_THIS_LATER"

@app.post("/handle_task")
async def handle_task(request: Request):
    try:
        payload = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    if payload.get("secret") != SECRET:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    # return 200 quickly
    asyncio.create_task(solve_quiz(payload))

    return {"status": "accepted", "message": "Quiz solving started"}
