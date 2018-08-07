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


def write_output_to_json(data, operation_name, folder):
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

def perform_ndvi(last_config, out_volume, out_folder):
    ''' Performs NDVI '''

    print("-> Start calculating NDVI...")
    for file_path in last_config["file_paths"]:
        filename = file_path.split("/")[-1]
        file_date = filename.split("_")[1]

        # Open input dataset
        file_path = "{0}/{1}".format(out_volume, file_path)
        in_dataset = gdal.Open(file_path)

        # Calculate ndvi
        ndvi_data = calc_ndvi(in_dataset, last_config)

        # Save output dataset
        folder_ndvi = create_folder(out_folder, "ndvi_first")
        out_file_path = "{0}/ndvi_{1}_epsg-{2}_first.tif".format(folder_ndvi, file_date, last_config["data_srs"].split(":")[-1])
        create_output_image(in_dataset, out_file_path, ndvi_data)

        # Warp out_files to create correct georeference
        out_file_path_warp = "{0}/ndvi_{1}_epsg-{2}.tif".format(out_folder, file_date, last_config["data_srs"].split(":")[-1])
        gdal.Warp(out_file_path_warp, out_file_path)

        print(" - NDVI calculated for {0}".format(filename))

    print("-> Finished calculating NDVI.")


def create_output_image(in_dataset, out_file_path, out_data):
    '''Create and save output dataset'''

    driver = gdal.GetDriverByName("GTiff")

    # Create output file from input (only one band)
    out_dataset = driver.Create(out_file_path, in_dataset.RasterXSize, in_dataset.RasterYSize, 1, gdal.GDT_Float32)

    # Add spatial information from input dataset
    out_dataset.SetGeoTransform(in_dataset.GetGeoTransform())
    out_dataset.SetProjection(in_dataset.GetProjection())

    # Add data
    band = out_dataset.GetRasterBand(1)
    band.WriteArray(out_data)
    band.SetNoDataValue(2)

    # Write to disk
    out_dataset.FlushCache()


def get_band_data(dataset, band_number):
    '''Returns band data for given dataset and band_name, the noDataValue is set to NaN'''

    # TODO check if band is in dataset

    band = dataset.GetRasterBand(band_number)
    data = band.ReadAsArray()

    # Set noDataValue to NaN
    data = data.astype(float)
    data = set_no_data(data, band.GetNoDataValue(), numpy.nan)

    return data


def set_no_data(data, cur, should):
    '''Set no data value'''

    data[data == cur] = should
    return data


def calc_ndvi(dataset, file_param):
    '''Returns ndvi for given red and nir band (no data is set to 2, ndvi in range [-1, 1])'''

    # Get band data
    red = get_band_data(dataset, file_param["band_order"]["B04"])
    nir = get_band_data(dataset, file_param["band_order"]["B08"])

    # Calculate NDVI
    ndvi = (nir - red) / (nir + red)
    ndvi = set_no_data(ndvi, numpy.nan, 2)
    return ndvi


def write_output(last_config, out_folder):
    '''Writes output's metadata to file'''

    data = {
        "product": last_config["product"],
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

    write_output_to_json(data, "ndvi", out_folder)