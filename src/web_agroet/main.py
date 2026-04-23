import os
import ee
import time
import gc
import geemap
import geopandas as gpd
import pandas as pd
from functools import partial

from src.web_agroet.utils.time import get_utc_offset
from src.web_agroet.utils.gee import get_one_per_day
from src.web_agroet.meteo.download_era5land import process_era5land
from src.web_agroet.geeet.eepredefined import landsat
from src.web_agroet.geeet.ptjpl import ptjpl_arid
from src.web_agroet.landsat.reproject import reproject_landsat_to_wgs84
from src.web_agroet.landsat.interpolation import process_landsat_interpolation
from src.web_agroet.landsat.calculation import add_vis_to_existing_files
from src.web_agroet.et.et0_landsat import process_et0_all_rasters_rio
from src.web_agroet.et.et_ml_predict import ETPredictor

def run_et_calculation(shape_path = './data/shape/circle.shp', start_date ='2024-07-01', end_date = '2024-07-31',
                       method='ML PT-JPL', gee_project='ee-dobralexey', max_cloud=10,
                       out_ptjpl = './data/images/', out_meteo = './data/', ml_model_path = './model/ml_et24.cbm',
                       sat_list = ["LANDSAT_8", "LANDSAT_9"], progress_callback=None):

    os.makedirs(out_ptjpl, exist_ok=True)

    # 01. initialize GEE
    if progress_callback:
        progress_callback(5, "🔧 Initializing GEE project connection...")

    '''
    try:
        ee.Initialize(project=gee_project)
    except Exception as e:
        ee.Authenticate(force=True)
        ee.Initialize(project=gee_project)
    '''

    # 02. shape read
    if progress_callback:
        progress_callback(10, "🗺️ Processing geometry boundaries...")

    gdf = gpd.read_file(shape_path)
    centroid = gdf['geometry'].centroid.to_crs("EPSG:4326")
    utc_offset = get_utc_offset(centroid.y[0], centroid.x[0])

    gdf_4326 = gdf.to_crs('EPSG:4326')
    geometry_4326 = gdf_4326.geometry.iloc[0]
    region = geometry_4326.__geo_interface__


    # 03. era5-land daily data get and transform
    #if progress_callback:
    #    progress_callback(20, "📡 Downloading ERA5-Land daily climate data...")

    process_era5land(geometry=centroid, start_date=start_date, end_date=end_date, output_path=out_meteo)

    #04. pt-jpl run and get bands
    if progress_callback:
        progress_callback(20, "💧 Running PT-JPL model calculations...")

    configured_ptjpl = partial(ptjpl_arid, utc_offset=utc_offset)
    workflow = [configured_ptjpl, landsat.extrapolate_LE]

    landsat_era5_ptjpl_collection = landsat.mapped_collection(
        workflow,
        date_start = start_date,
        date_end = end_date,
        region = region,
        max_cc = max_cloud,
        era5 = True,
        sat_list = sat_list,
        lai = "log-linear"
    )

    #bands_names = landsat_era5_ptjpl_collection.first().bandNames().getInfo()
    unique_landsat_era5_ptjpl_collection = get_one_per_day(landsat_era5_ptjpl_collection)
    geemap.ee_export_image_collection(unique_landsat_era5_ptjpl_collection, out_dir=out_ptjpl, region=region)
    

    # 05. Reproject to 4326 and rename all images
    if progress_callback:
        progress_callback(50, "🔄 Reprojecting images to target CRS...")

    lt_lst = [i for i in os.listdir(out_ptjpl) if i.endswith('.tif')]
    for img in lt_lst:
        img_rpr = reproject_landsat_to_wgs84(os.path.join(out_ptjpl, img))
    
    # 06. Caclulation ETrF
    if progress_callback:
        progress_callback(60, "📊 Calculating evaporation fraction (ETrF)...")

    process_et0_all_rasters_rio(out_ptjpl)

    # 07. Intepolation between dates
    if progress_callback:
        progress_callback(70, "✨ Interpolating spatial images...")

    img_lst = [os.path.join(out_ptjpl, i) for i in os.listdir(out_ptjpl) if i.endswith('.tif')]
    process_landsat_interpolation(img_lst, start_date, end_date, output_dir=out_ptjpl)

    time.sleep(0.1)
    gc.collect()

    #08. Calculation ETc/ET and ETs/ET and ASI
    if progress_callback:
        progress_callback(80, "🌿 Calculating vegetation indexes for ML model...")

    add_vis_to_existing_files(out_ptjpl)
    

    #09. Union with meteo and run ML model for every pixel
    if progress_callback:
        progress_callback(90, f"🤖 Making ET, ETc, ETs predictions using {method} method...")

    use_original_ptjpl = False
    if method == 'ML PT-JPL':
        use_original_ptjpl = False
    if method == 'Original PT-JPL':
        use_original_ptjpl = True

    df_meteo = pd.read_feather(out_meteo)

    predictor_ml = ETPredictor(
        images_dir=out_ptjpl,
        ml_model_path=ml_model_path,
        df_meteo=df_meteo,
        use_original_ptjpl=use_original_ptjpl
    )
    ml_results = predictor_ml.process_all_images(output_dir=out_ptjpl)
    if progress_callback:
        progress_callback(100, "✅ Processing complete!")

    return ml_results














