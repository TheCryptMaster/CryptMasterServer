import pyotp

# Lots of work left for this script

from utilities.database_connectivity import query_db, execute_db
from utilities.secret_generator import generate_secret
from utilities.key_crypt import encrypt_secret, decrypt_secret


# New users will require both a password, and a one time passcode
# Password will be used to encrypt the OTP seed info
# We will first try to decrypt the users seed with their password, if that fails, then user has sent bad password
# If successful, we decrypt the OTP seed, and verify the user has sent a good OTP.

OTP_ISSUER = 'Crypt Master'



def generate_user_creds(user_email, user_pass):
    otp = generate_secret()
    provisioning_uri = pyotp.totp.TOTP(otp).provisioning_uri(name=user_email, issuer_name=OTP_ISSUER)
    encrypted_otp = encrypt_secret(user_pass, otp)
    return provisioning_uri, encrypted_otp
