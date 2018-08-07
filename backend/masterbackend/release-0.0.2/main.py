
from convert.convert import copy_data
from filter.filter import unzip_data, extract_sentinel_2_data, combine_bands, combine_same_utm, reproject, \
                           merge_reprojected, transform_to_geotiff, write_output, clean_up, create_folder, read_parameters
from ndvi.ndvi import perform_ndvi, write_output as write_ndvi_output
from mintime.mintime import perform_min_time, write_output as write_min_time_output
# convert
IN_VOLUME  = "/data/MASTER/data/job_data"
OUT_VOLUME = "/data/MASTER/data/job_results"

CONFIG_FILE = "/data/MASTER/data/job_config/config.json"

process_graph = {
   "process_graph":{
      "process_id":"min_time",
      "args":{
         "imagery":{
            "process_id":"NDVI",
            "args":{
               "imagery":{
                  "process_id":"filter_daterange",
                  "args":{
                     "imagery":{
                        "process_id":"filter_bbox",
                        "args":{
                           "imagery":{
                              "product_id":"s2a_prd_msil1c"
                           },
                           "left":652000,
                           "right":672000,
                           "top":5161000,
                           "bottom":5181000,
                           "srs":"EPSG:32632"
                        }
                     },
                     "from":"2017 -01 -01",
                     "to":"2017 -01 -08"
                  }
               },
               "red":"B04",
               "nir":"B08"
            }
         }
      }
   }
}

TEMP_FOLDERS = {}  # tmp folder: tmp folder path -> deleted in the end
OUT_VOLUME = "/data/MASTER/data/job_data"

OUT_FOLDER = create_folder(OUT_VOLUME, "template_id")
PARAMS = read_parameters(CONFIG_FILE)
ARGS = PARAMS["process_graph"]["args"]
OUT_EPSG = "4326"

NDVI_OUT_VOLUME = "/data/"
NDVI_OUT_FOLDER = create_folder(OUT_VOLUME, "template_id_ndvi")

MINTIME_OUT_FOLDER = create_folder(OUT_VOLUME, "template_id_mintime")

def run_graph():
    
    # Run filter

    print("Start Sentinel 2 data extraction process...")

    # unzip_data(TEMP_FOLDERS, OUT_FOLDER, ARGS)
    # extract_sentinel_2_data(TEMP_FOLDERS, OUT_FOLDER, ARGS, PARAMS)
    # combine_bands(TEMP_FOLDERS, OUT_FOLDER)
    # combine_same_utm(TEMP_FOLDERS, OUT_FOLDER)
    # reproject(TEMP_FOLDERS, OUT_FOLDER, OUT_EPSG)
    # merge_reprojected(TEMP_FOLDERS, OUT_FOLDER, PARAMS, OUT_EPSG)
    # transform_to_geotiff(TEMP_FOLDERS, OUT_FOLDER, PARAMS)
    # write_output(ARGS, OUT_EPSG, OUT_FOLDER)
    # clean_up(TEMP_FOLDERS, OUT_FOLDER)

    print("Finished Sentinel 2 data extraction process.")
    
    # Run ndvi
    print("Start processing 'NDVI' ...")

    # NDVI_CONFIG_FILE = "/data/MASTER/data/job_data/template_id/files.json"
    # NDVI_PARAMS = read_parameters(NDVI_CONFIG_FILE)
    #
    # perform_ndvi(NDVI_PARAMS, NDVI_OUT_VOLUME, NDVI_OUT_FOLDER)
    # write_ndvi_output(NDVI_PARAMS, OUT_FOLDER)

    print("Finished 'NDVI' processing.")
    # Run min_time

    print("Start processing 'min_time' ...")

    MINTIME_CONFIG_FILE = "/data/MASTER/data/job_data/template_id/files.json"
    MINTIME_PARAMS = read_parameters(MINTIME_CONFIG_FILE)

    perform_min_time(OUT_FOLDER, OUT_VOLUME, MINTIME_PARAMS)
    write_min_time_output(MINTIME_PARAMS, OUT_FOLDER)

    print("Finished 'min_time' processing.")

    # Run convert
    # print("Start result data copy process...")
    # copy_data(CONFIG_FILE, IN_VOLUME, OUT_VOLUME)
    # print("Finish result data copy process.")


if __name__ == "__main__":
   run_graph()