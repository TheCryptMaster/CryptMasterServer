#!/usr/bin/python3

import pyotp

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Body, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis
import os
from dotenv import load_dotenv
from server_auth import CryptMasterClientAuth
from utilities.database_connectivity import query_db, execute_db
from utilities.secret_generator import generate_secret
from utilities.key_crypt import encrypt_secret, decrypt_secret


import pytz
import uvicorn



load_dotenv()


crypt_master_server_auth = CryptMasterClientAuth()

#@asynccontextmanager
#async def lifespan(app: FastAPI):
#    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
#    await FastAPILimiter.init(limiter)



utc = pytz.UTC
#app = FastAPI(lifespan=lifespan)
app = FastAPI()
fail_count = 0
fail_disable = datetime.now()
active_until = datetime.now()
keep_active = 5 #minutes
disable_time = 60 #minutes

totp_window = int(os.getenv('totp_window'))
#db_connection = os.getenv('db_connection')
#async_db_connection = os.getenv('async_db_connection')
#encryption_password = os.getenv('encryption_password')

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
    system_name = f'https://{host}.{domain}'
    return system_name

system_name = get_system_name()
if system_name == None:
    system_name = 'https://secure-api.cryptmaster.io'

origins = [
    f"{system_name}:2053",
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





def print_current_time():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S +00:00")
    return current_time





def get_secret(requested_password):
    encrypted_name = generate_secret(requested_password)
    get_secret = query_db(f"SELECT secret_pass FROM secrets WHERE secret_name = '{encrypted_name}'")
    if len(get_secret) == 0:
        return {'response': 'No secret found'}
    secret = decrypt_secret(generate_secret(encrypted_name), get_secret['secret_pass'][0])
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
    client_host = request.headers.get('x-forwarded-for', None)
    if client_host == None:
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




def check_password(user, user_pass, one_time_pass, client_host):
    global fail_count
    if check_fail_disable():
        raise HTTPException(status_code=403, detail="System Disabled")
    user_details = get_user_details(user)
    if len(user_details) == 0:
        print(f'{print_current_time()} {user} failed to logon at IP {client_host}.  User not found.')
        set_fail()
        raise HTTPException(status_code=403, detail="User Not Found!")
        return
    user_row, encrypted_otp = user_details[0], user_details[1]
    user_secret = generate_secret(user_pass)
    try:
        pyotp_seed = decrypt_secret(user_secret, encrypted_otp)
    except:
        set_fail()
        raise HTTPException(status_code=403, detail="Bad Password!")
        return
    totp = pyotp.TOTP(pyotp_seed)
    if not totp.verify(otp=one_time_pass, valid_window=totp_window):
        print(f'{print_current_time()} - User: {user} at IP Address {client_host} attempted to open api with an invalid OTP')
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid OTP")
    else:
        print(f'{print_current_time()} - User: {user} at IP Address {client_host} SUCCESSFULLY OPENED API')
        active_until = set_active_until()
        string_time = active_until.strftime("%m-%d-%Y_%Hh%Mm%Ss")
        response = {'response': 'Success', 'active_until': string_time}
        clear_fails()
    return response



@app.on_event("startup")
async def startup():
    limiter = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(limiter)






def add_pending_request(payload):
    encrypted_request = encrypt_secret(generate_secret('enrollment'), payload)
    check_existing = query_db(f"SELECT id pending_row, enrollment_attempts FROM pending_enrollments WHERE pending_enrollment = '{encrypted_request}'")
    if len(check_existing) != 0:
        pending_row, enrollment_attempts = check_existing['pending_row'][0], check_existing['enrollment_attempts'][0]
        new_attempt = enrollment_attempts + 1
        execute_db(f"UPDATE pending_enrollments SET enrollment_attempts = {new_attempt} WHERE id = {pending_row}")
        if new_attempt > 3:
            return {'response': 'This server has been banned'}
        else:
            return {'response': 'enrollment is still pending'}
    execute_db(f"INSERT INTO pending_enrollments(pending_enrollment) VALUES('{encrypted_request}')")
    return {'response': 'enrollment pending'}








#### VERSION 2.0 Endpoints - Current API Endpoints


@app.post("/v2/start_auth", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
def header_response(request: Request, payload=Body(...)):
    payload['ip_address'] = get_web_user_ip_address(request)
    allowed, response = crypt_master_server_auth.initiate_auth(payload)
    if not allowed:
        print('auth_fail_payload: ', payload)
        return Response("Unauthorized", 401,{'WWW-Authenticate': 'Digest realm="Protected"'})
    return response



@app.post("/v2/enable_api", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def validate_credentials(request: Request, payload=Body(...)):
    ip_address = get_web_user_ip_address(request)
    if check_fail_disable():
        print(f'{print_current_time()} - IP Address {ip_address} attempted to get secret while system is disabled.')
        set_fail()
        raise HTTPException(status_code=403, detail="API Disabled")
        return
    user = payload.get('user_name', None)
    user_pass = payload.get('user_pass', None)
    one_time_pass = str(payload.get('otp', None))
    if user == None or one_time_pass == None or user_pass == None:
        set_fail()
        raise HTTPException(status_code=403, detail="Invalid Credentials")
    response = check_password(user, user_pass, one_time_pass, ip_address)
    return response


@app.post("/v2/enroll_server", dependencies=[Depends(RateLimiter(times=1, seconds=120))])
def enroll_server(request: Request, payload=Body(...)):
    client_host = get_web_user_ip_address(request)
    payload['ip_address'] = client_host
    response = add_pending_request(payload)
    return response







@app.post("/v2/get_secret", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
def provide_secret(request: Request, payload=Body(...)):
    ip_address = get_web_user_ip_address(request)
    system_id = payload.get('system_id')
    encrypted_id = generate_secret(str(system_id))
    encrypted_ip = generate_secret(ip_address)
    if len(query_db(f"SELECT id FROM app_servers WHERE server_name = '{encrypted_id}' AND ip_address = '{encrypted_ip}'")) == 0:
        print(f'{print_current_time()} - IP Address {ip_address} attempted to get secret, and is not a valid server')
        set_fail()
        raise HTTPException(status_code=403, detail="ACCESS DENIED")
        return
    if not crypt_master_server_auth.validate_secret(payload.get('auth_response', None)):
        print(f'{print_current_time()} - IP Address {ip_address} attempted to get secret, with invalid credentials.')
        set_fail()
        raise HTTPException(status_code=403, detail="ACCESS DENIED")
        return
    elif check_fail_disable():
        print(f'{print_current_time()} - IP Address {ip_address} attempted to get secret while system is disabled.')
        set_fail()
        raise HTTPException(status_code=403, detail="API Disabled")
        return
    elif not check_active():
        print(f'{print_current_time()} - IP Address {ip_address} attempted to get secret.  OTP has not been provided.')
        return {'response': 'Authorized user must provide OTP'}
    requested_password = payload.get('requested_password', None)
    if requested_password == None:
        return {'response': 'No secret requested'}
    response = get_secret(requested_password)
    return response




#### VERSION 1.0 Endpoints - Will be removed in the near term





if __name__ == '__main__':
    uvicorn.run(app, host='0', port=api_port, ssl_keyfile='.privkey.pem', ssl_certfile='.fullchain.pem', reload=False)
