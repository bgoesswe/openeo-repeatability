import json
from os import makedirs, path
from shutil import copyfile


def read_parameters(config_file):
    ''' Return parameters from config file '''

    with open(config_file) as json_file:
        parameters = json.load(json_file)

    return parameters


def load_last_config(last_folder):
    with open("{0}/files.json".format(last_folder)) as json_file:
        config = json.load(json_file)

    return config


def copy_data(config_file, in_volume, out_volume):
    ''' Copies the data into the job result folder '''

    param = read_parameters(config_file)
    ARGS = param["process_graph"]["args"]
    # LAST_FOLDER = "{0}/{1}".format(in_volume, param["last"])
    # LAST_CONFIG = load_last_config(LAST_FOLDER)

    OUT_VOLUME = out_volume
    IN_VOLUME = in_volume

    out_dir = "{0}/{1}".format(OUT_VOLUME, ARGS["job_id"])

    if not path.exists(out_dir):
        makedirs(out_dir)

#    for file_path in LAST_CONFIG["file_paths"]:
#        file_path = "{0}/{1}".format(IN_VOLUME, file_path)
#        file_name = file_path.split("/")[-1]
#        copyfile(file_path, "{0}/{1}".format(out_dir, file_name))
#        print(" -> Copied file: " + file_path)