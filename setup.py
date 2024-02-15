# Lots of work left for this script

from utilities.database_connectivity import query_db, execute_db


# New users will require both a password, and a one time passcode
# Password will be used to encrypt the OTP seed info
# We will first try to decrypt the users seed with their password, if that fails, then user has sent bad password
# If successful, we decrypt the OTP seed, and verify the user has sent a good OTP.