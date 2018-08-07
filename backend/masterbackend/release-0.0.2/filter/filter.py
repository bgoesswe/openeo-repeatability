from shutil import copyfile, rmtree
from zipfile import ZipFile
from osgeo import gdal, osr
import json
from os import path, makedirs, listdir


def read_parameters(config_file):
    ''' Return parameters from config file '''

    with open(config_file) as json_file:
        parameters = json.load(json_file)

    return parameters


def build_new_granule_name_from_old(granule_name):
    '''Builds the corresponding new granule name from an old S2 name'''

    granule_name_split = granule_name.split("_")

    parts = {"proc_level": granule_name_split[3],
             "tile_number": granule_name_split[-2],
             "absolut_orbit": granule_name_split[-3],
             "date": granule_name_split[-4]}

    return "{0}_{1}_{2}_{3}".format(parts["proc_level"], parts["tile_number"], parts["absolut_orbit"], parts["date"])


def build_new_img_name_from_old(img_name):
    '''Builds the corresponding new image name form an old S2 name'''

    img_name_split = img_name.split(".")[0].split("_")

    parts = {"band": img_name_split[-1],
             "tile_number": img_name_split[-2],
             "date": img_name_split[-4]}

    return "{0}_{1}_{2}.jp2".format(parts["tile_number"], parts["date"], parts["band"])


def create_folder(base_folder, new_folder):
    '''Creates new_folder inside base_folder if it does not exist'''

    folder_path = "{0}/{1}".format(base_folder, new_folder)
    if not path.exists(folder_path):
        makedirs(folder_path)
    return folder_path


def write_output_to_json(data, operation_name, folder):
    '''Creates folder out_config in folder and writes data to json inside this new folder'''
    # folder_out_config = create_folder(folder, "out_config")

    # with open("{0}/out_{1}_config.json".format(folder, operation_name), "w") as outfile:
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


def unzip_data(temp_folders, out_folders, args):
    ''' Unzips the files from EODC storage to out volume '''

    print("-> Start data unzipping...")

    temp_folders["unzipped"] = create_folder(out_folders, "01_unzipped")

    for item in args["file_paths"]:

        # create a Out folder for each day (eg: /job_out/unzipped/2018-02-06/)
        unzip_path = create_folder(temp_folders["unzipped"], item["date"])

        # extract all files of current day
        if not isinstance(item["path"], list):
            item["path"] = [item["path"]]

        for zip_path in item["path"]:
            zip_ref = ZipFile(zip_path, 'r')
            zip_ref.extractall(unzip_path)
            zip_ref.close()

            print(" - Unzipped {0}".format(zip_path))

    print("-> Finished data unzipping.")


def extract_sentinel_2_data(temp_folders, out_folder, args, param):
    ''' Extracts data that is specified by PARAMS '''

    print("-> Start data extraction...")

    # Create Out folder
    temp_folders["extracted"] = create_folder(out_folder, "02_extracted")

    for day in listdir(temp_folders["unzipped"]):

        # Create Out folder for each day inside "extracted" folder
        folder_day = create_folder(temp_folders["extracted"], day)

        # Iterate over each day folder in unzipped (observation: path to archive on eodc storage)
        for observation in listdir("{0}/{1}".format(temp_folders["unzipped"], day)):
            for granule in listdir("{0}/{1}/{2}/GRANULE".format(temp_folders["unzipped"], day, observation)):

                dst_granule = granule
                # Check for old S2 naming convention
                if granule.startswith("S"):
                    dst_granule = build_new_granule_name_from_old(granule)

                # Create a folder for each granule
                folder_granule = create_folder(folder_day, dst_granule)

                img_path = "{0}/{1}/{2}/GRANULE/{3}/IMG_DATA".format(temp_folders["unzipped"], day, observation, granule)
                for img_name in listdir(img_path):
                    file_band = img_name.split("_")[-1].split(".")[0]

                    if not "filter_bands" in args or file_band in param["filter_bands"]["bands"]:

                        dst_img_name = img_name
                        # Check for old S2 naming convention
                        if img_name.startswith("S"):
                            dst_img_name = build_new_img_name_from_old(img_name)

                        src = "{0}/{1}".format(img_path, img_name)
                        dst = "{0}/{1}".format(folder_granule, dst_img_name)
                        copyfile(src, dst)

                        print(" - Extracted {0}".format(dst_img_name))

    print("-> Finished data extraction.")


def combine_bands(temp_folders, out_folder):
    '''Combines all specified bands per file'''

    print("-> Start combining bands...")

    # Create Out folder
    temp_folders["combined_bands"] = create_folder(out_folder, "03_combined_bands")

    # Iterate over each day
    for day in listdir(temp_folders["unzipped"]):

        # Create one folder per day
        folder_day = create_folder(temp_folders["combined_bands"], day)

        # Iterate over each granule
        for granule in listdir("{0}/{1}".format(temp_folders["extracted"], day)):

            # Get list of input files
            band_path_list = get_paths_for_files_in_folder \
                ("{0}/{1}/{2}/".format(temp_folders["extracted"], day, granule))
            band_path_list.sort()  # make sure bands are always in same order

            # Build out_path (filename without file extension and band number)
            out_filename = "{0}.vrt".format(band_path_list[0].split("/")[-1].split(".")[0][:-4])
            out_path = "{0}/{1}".format(folder_day, out_filename)

            # Combine all dataset bands in one vrt-file
            gdal.BuildVRT(out_path, band_path_list, separate=True, srcNodata=0)
            print(" - Combined bands for {0}".format(out_filename))

    print("-> Finished combining bands.")


def combine_same_utm(temp_folders, out_folder):
    '''Combines all files within one UTM zone in on vrt-file (per day)'''

    print("-> Start combining same UTM zone...")

    # Create Out folder
    temp_folders["utm"] = create_folder(out_folder, "04_combined_utm")

    # iterate over each day
    for day in listdir(temp_folders["unzipped"]):

        # Create one folder per day
        folder_day = create_folder(temp_folders["utm"], day)

        # Sort files after their UTM zone
        zones = {}
        for file in listdir("{0}/{1}".format(temp_folders["combined_bands"], day)):
            file_path = "{0}/{1}/{2}".format(temp_folders["combined_bands"], day, file)

            cur_zone = file[1:3]
            if cur_zone not in zones:
                zones[cur_zone] = [file_path]
            else:
                zones[cur_zone].append(file_path)

        # Iterate over UTM zones in dict
        for zone in zones.keys():
            # Build out_path
            out_filename = "T{0}_{1}.vrt".format(zone, day)
            out_path = "{0}/{1}".format(folder_day, out_filename)

            # Merge all vrt-files inside one UTM zone
            gdal.BuildVRT(out_path, zones[zone])
            print(" - Combined UTM for {0}".format(out_filename))

    print("-> Finished combining same UTM zone.")


def reproject(temp_folders, out_folder, out_epsg):
    '''Reprojects all UTM zones into specified reference system'''

    print("-> Start reprojection...")

    # Create Out folder with subfolders for each day
    temp_folders["reproject"] = create_folder(out_folder, "05_reproject")

    for day in listdir(temp_folders["unzipped"]):

        # Create one folder per day
        folder_day = create_folder(temp_folders["reproject"], day)

        for utm_file in listdir("{0}/{1}".format(temp_folders["utm"], day)):

            # Get input path
            in_path = "{0}/{1}/{2}".format(temp_folders["utm"], day, utm_file)

            # Build output path
            out_filename = "{0}_epsg{1}.vrt".format(utm_file.split(".")[0], out_epsg)
            out_path = "{0}/{1}".format(folder_day, out_filename)

            # Reproject each utm file to set epsg
            gdal.Warp(out_path, in_path, dstSRS="EPSG:{0}".format(out_epsg), format="vrt")
            print(" - Reprojected {0}".format(out_filename))

    print("-> Finished reprojection.")


def merge_reprojected(temp_folders, out_folder, params, out_epsg):
    '''Merges all reprojected files and applies bbox'''

    print("-> Start merging...")

    # Create Out folder
    temp_folders["merged"] = create_folder(out_folder, "06_merged")

    params["bbox_out_epsg"] = None

    for day in listdir(temp_folders["unzipped"]):

        # Get input path
        file_path_list = get_paths_for_files_in_folder("{0}/{1}/".format(temp_folders["reproject"], day))

        # Build output path
        out_filename = "filter-s2_{0}_epsg-{1}.vrt".format(day, out_epsg)
        out_path = "{0}/{1}".format(temp_folders["merged"], out_filename)

        if params["bbox_out_epsg"] is None:
            params["bbox_out_epsg"] = get_bbox(params["process_graph"]["args"], out_epsg)

        # Merge all files into one vrt-file
        gdal.BuildVRT(out_path, file_path_list, outputBounds=params["bbox_out_epsg"])
        print(" - Merged {0}".format(out_filename))

    print("-> Finished merging.")


def transform_to_geotiff(temp_folders, out_folder, params):
    '''Translates merged vrt-file to GeoTiff'''

    print("-> Start translation to GeoTiff...")

    for file in listdir(temp_folders["merged"]):

        # Get input path
        in_path = "{0}/{1}".format(temp_folders["merged"], file)

        # Build output path
        out_filename = "{0}.tif".format(file.split(".")[0])
        out_path = "{0}/{1}".format(out_folder, out_filename)

        # Translate vrt-file to GeoTiff
        gdal.Translate(out_path, in_path, outputBounds=params["bbox_out_epsg"])  # TODO show progress somehow (slow!)
        print(" - Translated {0}".format(out_filename))

    print("-> Finished translation to GeoTiff.")


def get_bbox(args, out_epsg):
    '''Returns bbox in specified reference system
    :return bbox:[left, bottom, right, top] - array of numbers'''

    bbox_epsg = args["filter_bbox"]["srs"].split(":")[1]

    # Transform bbox coordinates to reference system of data
    if out_epsg != bbox_epsg:

        # Get spatial reference system of the bbox and the specified one
        bbox_srs = osr.SpatialReference()
        bbox_srs.ImportFromEPSG(int(bbox_epsg))
        data_srs = osr.SpatialReference()
        data_srs.ImportFromEPSG(int(out_epsg))

        # Get Transformation
        transform = osr.CoordinateTransformation(bbox_srs, data_srs)

        # Transform all corner points
        left_bottom = transform.TransformPoint(args["filter_bbox"]["left"], args["filter_bbox"]["bottom"])
        left_top = transform.TransformPoint(args["filter_bbox"]["left"], args["filter_bbox"]["top"])
        right_top = transform.TransformPoint(args["filter_bbox"]["right"], args["filter_bbox"]["top"])
        right_bottom = transform.TransformPoint(args["filter_bbox"]["right"], args["filter_bbox"]["bottom"])

        # Find max/min for each corner
        left = min(left_bottom[0], left_top[0])
        right = max(right_bottom[0], right_top[0])
        bottom = min(left_bottom[1], right_bottom[1])
        top = max(left_top[1], right_top[1])

        if bottom > top:
            tmp = bottom
            bottom = top
            top = tmp

        if left > right:
            tmp = right
            right = left
            left = tmp

        return [left, bottom, right, top]

        # return [left, top, right, bottom]

    else:
        return [args["filter_bbox"]["left"], args["filter_bbox"]["bottom"], args["filter_bbox"]["right"], args["filter_bbox"]["top"]]


def write_output(args, out_epsg, out_folder):
    '''Writes output's metadata to file'''

    # TODO Bands in Metadaten -> Übergeben als Parameter / Kein empty array
    # bands = ARGS["filter_bbox"]["bands"]
    if not "filter_bbox" in args["filter_bbox"]:
        bands = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "TCI"]
    else:
        bands = args["filter_bbox"]["bands"]

    # save band_order
    bands.sort()
    order = range(1, len(bands ) +1)
    band_order = dict(zip(bands, order))

    data = {"product": "Sentinel-2",
            "operations": ["filter-s2"],
            "band_order": band_order,
            "data_srs": "EPSG:{0}".format(out_epsg),
            "file_paths": get_paths_for_files_in_folder(out_folder),
            "extent": {
                "bbox": {
                    "top": args["filter_bbox"]["top"],
                    "bottom": args["filter_bbox"]["bottom"],
                    "left": args["filter_bbox"]["left"],
                    "right": args["filter_bbox"]["right"]},
                "srs": args["filter_bbox"]["srs"]},
            }

    # TODO Anders
    cropped_paths = []
    for path in data["file_paths"]:
        cropped_paths.append(path.split("/", 2)[2])
    data["file_paths"] = cropped_paths

    write_output_to_json(data, "filter-s2", out_folder)


def clean_up(temp_folders, out_folder):
    '''Deletes all unnecessary folders'''

    print("-> Start clean up...")

    for folder_path in temp_folders.keys():
        rmtree(temp_folders[folder_path])

    print("-> Finished clean up.")
    print(listdir(out_folder))