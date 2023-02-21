#!/usr/bin/python3

import pyotp
import time
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
import os
from dotenv import load_dotenv


import pytz
import uvicorn



load_dotenv()
api_port = 20120
utc = pytz.UTC
app = FastAPI()



db_connection = os.getenv('db_connection')
async_db_connection = os.getenv('async_db_connection')
encryption_password = os.getenv('encryption_password')











origins = [
    "https://api.themorphium.io:8095",
    "http://localhost",
    "http://localhost:8095"
]





## STARTUP - Rate Limiter
@app.on_event("startup")
async def startup():
    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter)

# GETS



if __name__ == '__main__':
    uvicorn.run(app, host='0', port=api_port, ssl_keyfile='.privkey.pem', ssl_certfile='.fullchain.pem', debug=False, reload=False)
