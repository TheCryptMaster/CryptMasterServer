#!/usr/bin/python3

import pyotp

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import os
from dotenv import load_dotenv

from utilities.database_connectivity import query_db, execute_db
from utilities.secret_generator import generate_secret
from utilities.key_crypt import encrypt_secret, decrypt_secret


import pytz
import uvicorn



load_dotenv()



#@asynccontextmanager
#async def lifespan(app: FastAPI):
#    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
#    await FastAPILimiter.init(limiter)



utc = pytz.UTC
#app = FastAPI(lifespan=lifespan)
app = FastAPI()
authenticated_servers_file = '.authenticated_servers'
fail_count = 0
fail_disable = datetime.now()
active_until = datetime.now()
keep_active = 5 #minutes
disable_time = 60 #minutes

totp_window = int(os.getenv('totp_window'))
db_connection = os.getenv('db_connection')
async_db_connection = os.getenv('async_db_connection')
encryption_password = os.getenv('encryption_password')
test_password = "You're did it!"
pyotp_seed = os.getenv('pyotp_seed')
pyotp_issuer = os.getenv('pyotp_issuer')
api_port = int(os.getenv('api_port'))

def get_system_name():
    lookup = query_db("SELECT host_name, domain_name FROM cryptmaster_warden ORDER BY ID ASC LIMIT 1")
    if len(lookup) == 0:
        return None
    encrypted_domain, encrypted_host = lookup['domain_name'][0], lookup['host_name'][0]
    domain = decrypt_secret(generate_secret('domain'), encrypted_domain)
    host = decrypt_secret(generate_secret('hostname'), encrypted_host)



origins = [
    "https://secure-api.themorphium.io:2053",
    "http://localhost",
    "http://localhost:2053"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






def get_authenticated_servers():
    with open(authenticated_servers_file) as f:
        authenticated_servers = f.read().splitlines()
    return authenticated_servers




def get_secret(requested_password):
    if requested_password == 'test_password':
        secret = test_password
    elif requested_password == 'db_connection':
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




def get_user_details(user_name):
    user_details = []
    user_name = generate_secret(user_name)
    execute_db(f"UPDATE user_accounts SET is_active = False WHERE now() > active_until AND is_active = True")
    user_lookup = query_db(f"SELECT id user_row, user_otp_hash FROM user_accounts WHERE username = '{user_name}' AND is_active = True")
    if len(user_lookup) != 0:
        user_details = [int(user_lookup['user_row'][0]), user_lookup['user_otp_hash'][0]]
    return user_details




def check_password_v2(user, user_pass, one_time_pass, client_host):
    global fail_count
    if check_fail_disable():
        raise HTTPException(status_code=403, detail="System Disabled")
    user_details = get_user_details(user)
    if len(user_details) == 0:
        set_fail()
        raise HTTPException(status_code=403, detail="User Not Found!")
        return
    user_row, encrypted_otp = user_details[0], user_details[1]
    user_secret = generate_secret(user_pass)
    try:
        pyotp_seed = decrypt_secret(user_secret, encrypted_otp)[1:-1]
    except:
        set_fail()
        raise HTTPException(status_code=403, detail="Bad Password!")
        return
    totp = pyotp.TOTP(pyotp_seed)
    if not totp.verify(otp=one_time_pass, valid_window=totp_window):
        print(f'User: {user} at IP Address {client_host} attempted to open api with an invalid OTP')
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid OTP")
    else:
        print(f'User: {user} at IP Address {client_host} SUCCESSFULLY OPENED API')
        active_until = set_active_until()
        string_time = active_until.strftime("%m-%d-%Y_%Hh%Mm%Ss")
        response = {'response': 'Success', 'active_until': string_time}
        clear_fails()
    return response



@app.on_event("startup")
async def startup():
    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter)













#### VERSION 2.0 Endpoints - Current API Endpoints

@app.post("/v2/enable_api", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def validate_credentials(request: Request, payload=Body(...)):
    client_host = get_web_user_ip_address(request)
    if check_fail_disable():
        print(f'IP Address {client_host} attempted to get secret while system is disabled.')
        set_fail()
        raise HTTPException(status_code=403, detail="API Disabled")
        return
    user = payload.get('user_name', None)
    user_pass = payload.get('user_pass', None)
    one_time_pass = str(payload.get('otp', None))
    if user == None or one_time_pass == None or user_pass == None:
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    response = check_password_v2(user, user_pass, one_time_pass, client_host)
    return response






@app.post("/v2/get_secret")
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




#### VERSION 1.0 Endpoints - Will be removed in the near term





@app.post("/get_secret")
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
