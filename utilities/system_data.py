import platform
import subprocess

def get_system_id():
    try:
        if platform.system() == 'Windows':
            # Windows
            command = "wmic diskdrive get SerialNumber"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            serial_number = result.stdout.split()[1].strip()
            return clean_result(serial_number)
        elif platform.system() == 'Linux':
            # Linux
            command = "udevadm info --query=all --name=/dev/sda | grep ID_SERIAL_SHORT"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            serial_number = result.stdout.split('=')[1].strip()
            return clean_result(serial_number)
        elif platform.system() == 'Darwin':
            # MacOS
            command = "system_profiler SPStorageDataType | grep 'Serial Number' | awk '{print $3}'"
            result = subprocess.run(command, capture_output=True, text=True, shell=True)
            serial_number = result.stdout.strip()
            return clean_result(serial_number)
        else:
            return "Unknown operating system"
    except Exception as e:
        print("Error:", e)
        return None

def clean_result(string_info):
    new_string = ''
    for letter in string_info:
        if letter not in ['_', '.']:
            new_string += letter
    return new_string