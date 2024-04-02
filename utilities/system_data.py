import uuid

def get_system_id():
    id = uuid.uuid1()
    return id.hex[-24:]

def clean_result(string_info):
    new_string = ''
    for letter in string_info:
        if letter not in ['_', '.']:
            new_string += letter
    return new_string