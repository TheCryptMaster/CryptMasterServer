#!/usr/bin/python3

import pyotp
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import os
from dotenv import load_dotenv


import pytz
import uvicorn



load_dotenv()

utc = pytz.UTC
app = FastAPI()
authenticate_users_file = '.authenticated_users'
authenticated_servers_file = '.authenticated_servers'
fail_count = 0
fail_disable = datetime.now()
active_until = datetime.now()
keep_active = 5 #minutes
disable_time = 60 #minutes


db_connection = os.getenv('db_connection')
async_db_connection = os.getenv('async_db_connection')
encryption_password = os.getenv('encryption_password')
pyotp_seed = os.getenv('pyotp_seed')
pyotp_issuer = os.getenv('pyotp_issuer')
api_port = int(os.getenv('api_port'))




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



def get_authenticated_users():
    with open(authenticate_users_file) as f:
        authenticated_users = f.read().splitlines()
    return authenticated_users



def get_authenticated_servers():
    with open(authenticated_servers_file) as f:
        authenticated_servers = f.read().splitlines()
    return authenticated_servers


def check_password(user, one_time_pass, client_host):
    global fail_count
    if check_fail_disable():
        raise HTTPException(status_code=403, detail="System Disabled")
    users = get_authenticated_users()
    if len(users) == 0:
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
        return
    authenticated_users = {}
    i = 0
    while i < len(users):
        account = users(i)
        i += 1
        user_secret = users(i)
        i += 1
        authenticated_users = authenticated_users | {account:user_secret}
    pyotp_seed = authenticated_users.get(user, None)
    totp = pyotp.totp.TOTP(pyotp_seed).provisioning_uri(name=user, issuer_name=pyotp_issuer)
    if user.lower() not in [*authenticated_users]:
        print(f'User: {user} at IP Address {client_host} attempted to open api and is not an authorized user')
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
        return
    elif one_time_pass != totp.now():
        print(f'User: {user} at IP Address {client_host} attempted to open api with an invalid OTP')
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    else:
        print(f'User: {user} at IP Address {client_host} SUCCESSFULLY OPENED API')
        active_until = set_active_until()
        string_time = active_until.strftime("%m-%d-%Y_%Hh%Mm%Ss")
        response = {'response': 'Success', 'active_until': string_time}
        clear_fails()
    return response



def get_secret(requested_password):
    if requested_password == 'db_connection':
        secret = db_connection
    elif requested_password == 'async_db_connection':
        secret = async_db_connection
    elif requested_password == 'encryption_password':
        secret = encryption_password
    else:
        secret = None
    response = {'response': 'SUCCESS', 'secret': secret}
    return response


def check_fail_disable():
    return fail_disable > datetime.now()

def set_fail():
    global fail_count, fail_disable
    fail_count += 1
    if fail_count >= 3:
        fail_disable = datetime.now() + timedelta(minutes=disable_time)
    return


def clear_fails():
    global fail_count
    fail_count = 0
    return




def check_active():
    current_time = datetime.now()
    return current_time < active_until


def set_active_until():
    global active_until
    active_until = datetime.now() + timedelta(minutes=keep_active)
    return active_until





def get_web_user_ip_address(request):
    client_host = request.client.host
    return client_host




@app.on_event("startup")
async def startup():
    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter)



@app.post("/enable_api", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def validate_credentials(request: Request, payload=Body(...)):
    client_host = get_web_user_ip_address(request)
    if check_fail_disable():
        print(f'IP Address {client_host} attempted to get secret while system is disabled.')
        set_fail()
        raise HTTPException(status_code=403, detail="API Disabled")
        return
    user = payload.get('user_name', None)
    one_time_pass = payload.get('otp', None)
    if user == None or one_time_pass == None:
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    response = check_password(user, one_time_pass, client_host)
    return response






@app.post("/get_secret", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def provide_secrete(request: Request, payload=Body(...)):
    authenticated_servers = get_authenticated_servers()
    client_host = get_web_user_ip_address(request)
    if client_host not in authenticated_servers:
        print(f'IP Address {client_host} attempted to get secret, and is not an authorized client')
        set_fail()
        raise HTTPException(status_code=403, detail="ACCESS DENIED")
        return
    elif check_fail_disable():
        print(f'IP Address {client_host} attempted to get secret while system is disabled.')
        set_fail()
        raise HTTPException(status_code=403, detail="API Disabled")
        return
    elif not check_active():
        print(f'IP Address {client_host} attempted to get secret.  OTP has not been provided.')
        return {'response': 'Authorized user must provide OTP'}
    requested_password = payload.get('requested_password', None)
    if requested_password == None:
        return {'response': 'No secret requested'}
    response = get_secret(requested_password)
    return response




if __name__ == '__main__':
    uvicorn.run(app, host='0', port=api_port, ssl_keyfile='.privkey.pem', ssl_certfile='.fullchain.pem', reload=False)
