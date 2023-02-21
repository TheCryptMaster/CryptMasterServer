#!/usr/bin/python3

# ToDo reward calculation for future rewards for 1 wallet
# ToDo Add user save post


from fastapi import FastAPI, Body, Depends, HTTPException, status, UploadFile, File, Request, Form, Header, Response, Security
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from dotenv import load_dotenv
from pydantic import BaseModel

import pytz
import uvicorn



load_dotenv()
api_port = 8095
utc = pytz.UTC
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")





#https://codevoweb.com/api-with-python-fastapi-and-mongodb-jwt-authentication/

@AuthJWT.load_config
def get_config():
    return Settings()












origins = [
    "https://api.themorphium.io:8095",
    "http://localhost",
    "http://localhost:8095"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





## STARTUP - Rate Limiter
@app.on_event("startup")
async def startup():
    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter)

# GETS



if __name__ == '__main__':
    uvicorn.run(app, host='0', port=api_port, ssl_keyfile='.privkey.pem', ssl_certfile='.fullchain.pem', debug=False, reload=False)
