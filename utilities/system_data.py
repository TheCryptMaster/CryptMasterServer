import os
import sys


def get_system_id():
    ### print('Currently only working with ubuntu')
    """ Find OS and run appropriate read mobo serial num command"""
    os_type = sys.platform.lower()
    if "darwin" in os_type:
        command = "ioreg -l | grep IOPlatformSerialNumber"
    elif "win" in os_type:
        command = "wmic bios get serialnumber"
    elif "linux" in os_type:
        command = "ls -l /dev/disk/by-uuid"
    response = response = os.popen(command).read()
    return locate_serial(response)



def locate_serial(response):
    serial, serial_text = '', None
    words = response.split()
    for word in words:
        if '-' in word:
            serial_text = word
            break
    if serial_text:
        for letter in word:
            if letter != '-':
                serial += letter
    return serial