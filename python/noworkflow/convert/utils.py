''' Utilities for Sentinel-2 data extraction '''

import json

CONFIG_FILE = "test_config.json"
IN_MOUNTS_FILE = "input_mounts.json"

def read_parameters():
    ''' Return parameters from config file '''

    with open(CONFIG_FILE) as json_file:
        parameters = json.load(json_file)

    return parameters

def read_input_mounts():
    ''' Return parameters from config file '''

    with open(IN_MOUNTS_FILE) as json_file:
        input_mounts = json.load(json_file)

    return input_mounts
