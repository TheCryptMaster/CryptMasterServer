UPDATES

Work is nearly complete on version 2.0.  Current dev has been merged in to main.  Will be starting a new version 2 branch to continue development on version 2.

# Crypt Master Server
A Secure Server for controlling keys to sensitive databases

The Crypt Master Client is available here: https://github.com/TheCryptMaster/CryptMaster


## Recommended system architecture
Dedicated hardware is paramount to providing physical security.  It is recommended that you create a separate subnet exclusively for your crypt keeper, and use proper firewall rules to only allow necessary access to the API Port.  If you do allow any remote access to your key crypt, it should only be allowed at your firewall for the duration of your administrative session, and then access should be immediately removed.  You can set up Crypt Keeper on any reasonable device.  Best recommendation is to use a mini pc.  Dell Micro and Intel Nuc are both great picks.  You should install VMWare Esxi 7 as the base operating system.  7 supports a wide range of hardware, and has fewer restrictions than 8.  ESXi is free.  If your server has a small amount of storage, you can use the boot config file in the vmware_boot_config directory to install ESXi in the smallest footprint.  The minimum hard drive size is 128gb under these conditions.  With ESXi installed, create a single virtual machine for the Crypt Keeper with the leftover available resources.

With the architecture out of the way, you should use the latest version of Ubuntu as the base OS.  During installation it is recommended that you add encryption to the LVM.  If you installed this as a virtual machine, you should still be able to remote in to your server, and gain console access in order to boot your crypt keeper.  You will need to enter the encryption password at bootup.  As previously stated, always close off remote access to your key crypt (and hypervisor if you are using one) when you are done administering your system.


## SETUP
Create two empty files:

touch .authenticated_users
touch .authenticated_servers

Install requirements

pip install -r requirements.txt

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg
sudo apt-get update


sudo apt-get install redis-server supervisor certbot gnupg2 wget vim postgresql-16 postgresql-contrib-16 
sudo systemctl enable postgresql
sudo systemctl start postgresql

sudo apt full-upgrade

sudo sed -i '/^host/s/ident/md5/' /etc/postgresql/16/main/pg_hba.conf
sudo sed -i '/^local/s/peer/trust/' /etc/postgresql/16/main/pg_hba.conf
echo "host all all 0.0.0.0/0 md5" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf


## Create DB User Account with temporary password
sudo -u postgres createuser --superuser initial_db_user -P

## Create Empty DB
sudo -u postgres createdb initial_db_user_db --owner=initial_db_user



create certificate:
sudo certbot certonly -d your-api-name.your-domain.com

copy cert in to running folder:
sudo cp /etc/letsencrypt/live/your-api-name.your-domain.com/fullchain.pem .fullchain.pem
sudo cp /etc/letsencrypt/live/your-api-name.your-domain.com/privkey.pem .privkey.pem

modify files:
sudo chmod +x crypt_keeper.py
sudo chown yourname:yourname *.pem

Copy SUPERVISOR_EXAMPLE to /etc/supervisor/conf.d/crypt_keeper.conf
Modify example as necessary.

Create new .env file using the ENV_EXAMPLE as a loose template.  Tailor this to your needs.

Set your one time password seed in the env file.  You can use your own password, or use:

import pyotp
pyotp.random_base32()


Remove all remote access to the server running this service.  Secure firewall to only allow your api port to this server.  Configuring your network is beyond the scope of these instructions.

WARNING!!!! You will be storing your actual passwords in the .env file.  It is imperative that there is not any remote command prompt left open to this server.



## Adding or Removing Users and Servers

python3 add_remove.py

Welcome to the Crypt Keeper

Which action would you like to perform?:

1) Add Authenticated User
2) Remove Authenticated User
3) Add Allowed Server
4) Remove Allowed Server



Logging 

Find the current random ident
sudo ls /var/log/supervisor/crypt_keeper-std*

STDOUT
sudo tail -f /var/log/supervisor/crypt_keeper-stdout---supervisor-SOMERANDOMIDENT.log

STDERR
sudo tail -f /var/log/supervisor/crypt_keeper-stderr---supervisor-SOMERANDOMIDENT.log

Check status and restart service
sudo supervisorctl status
sudo supervisorctl stop crypt_keeper
sudo supervisorctl start crypt_keeper
sudo supervisorctl restart crypt_keeper


## API Functions
https://your-api-name.your-domain.com:2053/enable_api

Payload = 
{
 "user_name": "user@your-domain.com",
 "otp": '1234567'
}


https://your-api-name.your-domain.com:2053/get_secret

Payload = 
{
 "requested_password": "test_password"
}
