import json
from os import path, makedirs, listdir
from osgeo import gdal
import numpy

def read_parameters(config_file):
    ''' Return parameters from config file '''

    with open(config_file) as json_file:
        parameters = json.load(json_file)

    return parameters

def load_last_config(last_folder):
    with open("{0}/files.json".format(last_folder)) as json_file:
        config = json.load(json_file)

    return config

def create_folder(base_folder, new_folder):
    '''Creates new_folder inside base_folder if it does not exist'''

    folder_path = "{0}/{1}".format(base_folder, new_folder)
    if not path.exists(folder_path):
        makedirs(folder_path)
    return folder_path


def write_output_to_json(data, folder):
    '''Creates folder out_config in folder and writes data to json inside this new folder'''

    with open("{0}/files.json".format(folder), "w") as outfile:
        json.dump(data, outfile)


def get_paths_for_files_in_folder(folder_path):
    '''Returns a list of all file paths inside the given folder'''

    file_list = listdir(folder_path)

    files = []
    for file_path in file_list:
        if path.isfile(path.join(folder_path, file_path)):
            files.append("{0}/{1}".format(folder_path, file_path))

    return files

def perform_min_time(out_folder, out_volume, last_config):
    ''' Performs min time '''

    print("-> Start calculating minimal NDVI...")
    # Create Out folders
    folder_stack_time_vrt = create_folder(out_folder, "stack_time_vrt")
    folder_stack_time_tif = create_folder(out_folder, "stack_time_tif")

    # Define output paths
    filename_part = "-time_epsg-{0}".format(last_config["data_srs"].split(":")[-1])
    path_time_stack_vrt = "{0}/stack{1}.vrt".format(folder_stack_time_vrt, filename_part)
    path_time_stack_tif = "{0}/stack{1}.tif".format(folder_stack_time_tif, filename_part)
    path_min_time = "{0}/min{1}.tif".format(out_folder, filename_part)

    abs_file_paths = [out_volume + "/" + file_path for file_path in last_config["file_paths"]]

    # Combine all files into one (as different bands -> make sure they can be put on top of each other)
    gdal.BuildVRT(path_time_stack_vrt, abs_file_paths, separate=True)
    gdal.Translate(path_time_stack_tif, path_time_stack_vrt)

    dataset = gdal.Open(path_time_stack_tif)
    data = numpy.zeros((len(last_config["file_paths"]), dataset.RasterYSize, dataset.RasterXSize))
    out_dataset = create_out_dataset(dataset, path_min_time)  # Save dummy out dataset to be filled with data

    for band_num in range(0, len(last_config["file_paths"])):

        band = dataset.GetRasterBand(band_num + 1)
        file_data = band.ReadAsArray()

        # Save data to dict
        data[band_num] = file_data

    min_time_data = numpy.fmin.reduce(data)

    # Write data to dataset
    fill_dataset(out_dataset, min_time_data)

    print("-> Finished calculating minimal NDVI")


def create_out_dataset(in_dataset, out_path):
    '''Create output dataset'''

    driver = gdal.GetDriverByName("GTiff")

    # Create output file from input (only one band)
    out_dataset = driver.Create(out_path, in_dataset.RasterXSize, in_dataset.RasterYSize, 1, gdal.GDT_Float32)

    # Add spatial information from input dataset
    out_dataset.SetGeoTransform(in_dataset.GetGeoTransform())
    out_dataset.SetProjection(in_dataset.GetProjection())

    # Write to disk
    out_dataset.FlushCache()

    return out_dataset


def fill_dataset(dataset, data):
    '''Fill empty dataset with data'''

    # Add data
    band = dataset.GetRasterBand(1)
    band.WriteArray(data)
    band.SetNoDataValue(2)

    # Write to disk
    dataset.FlushCache()


def write_output(last_config, out_folder):
    '''Writes output's metadata to file'''

    data = {"product": last_config["product"],
            "operations": last_config["operations"] + ["ndvi"],
            "data_srs": last_config["data_srs"],
            "file_paths": get_paths_for_files_in_folder(out_folder),
            "extent": last_config["extent"]
            }

    # TODO Anders
    cropped_paths = []
    for path in data["file_paths"]:
        cropped_paths.append(path.split("/", 2)[2])
    data["file_paths"] = cropped_paths

    write_output_to_json(data, out_folder)