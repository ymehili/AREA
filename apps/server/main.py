from fastapi import FastAPI, Request
from datetime import datetime
import socket

app = FastAPI()

@app.get("/about.json")
async def about(request: Request):
    return {
        "client": {
            "host": request.client.host
        },
        "server": {
            "current_time": datetime.now().isoformat()
        }
    }

@app.get("/")
async def root():
    return {"message": "Server is running"}
