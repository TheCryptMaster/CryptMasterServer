#!/usr/bin/python3

import pyotp
import time
from datetime import datetime, timedelta
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
pyotp_seed = os.getenv('pyotp_seed')
pyotp_issuer = os.getenv('pyotp_issuer')
authenticate_users_file = '.authenticated_users'
authenticated_servers_file = '.authenticated_servers'



def get_authenticated_users():
    with open(authenticate_users_file) as f:
        authenticated_users = f.read().splitlines()
    return authenticated_users



def get_authenticated_servers():
    with open(authenticated_servers_file) as f:
        authenticated_servers = f.read().splitlines()
    return authenticated_servers


def check_password(user, one_time_pass):
    authenticated_users = get_authenticated_users()
    totp = pyotp.totp.TOTP(pyotp_seed).provisioning_uri(name=user, issuer_name=pyotp_issuer)
    if user.lower() not in authenticated_users:
        response = {'response': 'Invalid User'}
    elif totp != one_time_pass:
        response = {'response': 'Invalid One Time Passcode'}
    else:
        active_until = set_active_until()
        string_time = active_until.strftime("%m-%d-%Y_%Hh%Mm%Ss")
        response = {'response': 'Success', 'active_until': string_time}
    return response



keep_active = 5 #minutes

active_until = datetime.now()


def check_active():
    current_time = datetime.now()
    return current_time < active_until


def set_active_until():
    global active_until
    active_until = datetime.now() + timedelta(minutes=keep_active)
    return active_until




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
