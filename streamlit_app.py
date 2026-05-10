import io
import os
import glob
import base64
import shutil
import zipfile
import folium
import tempfile
import rasterio
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st
import branca.colormap as cm
import ee
import json
from PIL import Image
from rasterio.mask import mask
from shapely.geometry import mapping
from folium import plugins
from streamlit_folium import st_folium
from datetime import date, datetime
from pathlib import Path
from src.web_agroet.main import run_et_calculation
from scipy.signal import savgol_filter


TRANSLATIONS = {
    "en": {
        "page_title": "ML PT-JPL Model Interface",
        "page_icon": "logo.png",
        "title": "ML PT-JPL Model Web Interface",
        "input_params": "📝 Input Parameters",
        "select_area_method": "Select area input method:",
        "upload_shapefile": "Upload shapefile",
        "draw_polygon": "Draw polygon on map",
        "upload_file_prompt": "Upload shapefile (.zip (shp), .geojson, .gpkg)",
        "shapefile_loaded_zip": "✅ Shapefile loaded from ZIP: ",
        "geojson_loaded": "✅ GeoJSON loaded: ",
        "gpkg_loaded": "✅ GeoPackage loaded: ",
        "error_no_shp": "❌ No .shp file found in the ZIP archive",
        "error_read_file": "❌ Error reading file: ",
        "num_features": "📊 Number of features: ",
        "crs_label": "🗺️ CRS: ",
        "polygon_drawn": "✅ Polygon drawn successfully!",
        "polygon_loaded": "✅ Polygon loaded from session.",
        "date_range": "📅 Date Range",
        "start_date": "Start Date",
        "end_date": "End Date",
        "select_method": "Select Method",
        "method_help": "Choose between Machine Learning PT-JPL or Original PT-JPL model",
        "max_cloud": "Maximum Cloud Cover (%)",
        "cloud_help": "Maximum allowed cloud cover percentage",
        "output_locations": "💾 Output Settings",
        "out_ptjpl_label": "Output folder for Landsat PT-JPL images (temporary)",
        "out_ptjpl_help": "Temporary path for PT-JPL output images",
        "out_meteo_label": "Output path for ERA5-Land meteorological file (temporary)",
        "out_meteo_help": "Temporary path for meteorological data",
        "processing_results": "⚙️ Processing & Results",
        "current_config": "Current Configuration",
        "config_start": "Start Date",
        "config_end": "End Date",
        "config_method": "Method",
        "config_cloud": "Max Cloud",
        "config_out_ptjpl": "PT-JPL Output",
        "config_out_meteo": "Meteo Output",
        "run_button": "🚀 Run PT-JPL Model",
        "errors_upload": "Please upload a shapefile",
        "errors_draw": "Please draw a polygon on the map",
        "errors_dates": "Start date must be before end date",
        "errors_cloud": "Max cloud must be between 0 and 100",
        "progress_complete": "✅ Processing completed successfully!",
        "results_header": "📊 Results",
        "success_message": "Processing completed! Use the download buttons above to save the results.",
        "error_processing": "❌ Error during processing: ",
        "sidebar_instructions": "ℹ️ Instructions",
        "sidebar_steps": """
        1. **Select area input method** - either upload a shapefile or draw a polygon on the map (one agricultural field)
        2. **Choose date range** for the analysis (no more than one year)
        3. **Select method** (ML PT-JPL or Original PT-JPL)
        4. **Set maximum cloud cover** percentage
        5. **Click 'Run PT-JPL Model'** to start processing
        6. **Download results** using the buttons that appear after processing
        """,
        "map_subheader": "Draw your area of interest",
        "map_background": "Choose a map background:",
        "map_viewer": "🗺️ Map Viewer",
        "shapefile_loaded_sidebar": "✅ Shapefile loaded: ",
        "shapefile_info": "Shapefile Info",
        "crs": "CRS: ",
        "features": "Features: ",
        "area": "Total Area: ",
        "sq_units": " sq units",
        "tiff_folder_not_found": "TIFF folder '{folder}' not found. Please check the path.",
        "no_tiff_files": "No TIFF files found in '{folder}'",
        "date_parse_error": "Could not parse date from filename: ",
        "no_valid_tiff": "No valid date-formatted TIFF files found",
        "map_controls": "Map Controls",
        "select_date": "Select Date",
        "select_band": "Select Band",
        "status_info": "📅 Selected: {date}\n🎯 Band: {band}/{total}",
        "map_subheader_date": "{date} \n **{band_label} - Band {band}**",
        "cropping_spinner": "🔄 Cropping TIFF to shapefile boundary and creating map...",
        "band_stats": "📊 Band Statistics (Cropped Area)",
        "min": "Min",
        "max": "Max",
        "mean": "Mean",
        "std_dev": "Std Dev",
        "histogram_x": "Band {band} Value",
        "histogram_y": "Frequency",
        "histogram_title": "Histogram - {date} Band {band}",
        "file_info": "ℹ️ File Information",
        "file_name": "File: ",
        "original_crs": "Original CRS: ",
        "original_bounds": "Original Bounds: ",
        "original_dims": "Original Dimensions: ",
        "num_bands": "Number of bands: ",
        "data_type": "Data type: ",
        "nodata": "NoData value: ",
        "cropped_info": "Cropped to AOI:",
        "cropped_dims": "Cropped Dimensions: ",
        "cropped_bounds": "Cropped Bounds: ",
        "valid_pixels": "Valid pixels: ",
        "error_map": "❌ Error creating map: ",
        "map_info": "Please ensure the TIFF file overlaps with the shapefile and contains valid geospatial data.",
        "gee_init_failed": "❌ GEE initialization failed: ",
        "language_selector": "🌐 Language / Язык",
        "en": "English",
        "ru": "Русский",
        "download_all_tiffs": "📥 Download TIFF Files",
        "download_meteo": "📥 Download Meteodata",
        "download_timeseries": "📥 Download Timeseries",
        "download_single_tiff": "📥 Download This TIFF"
    },
    "ru": {
        "page_title": "Интерфейс модели ML PT-JPL",
        "page_icon": "logo.png",
        "title": "Веб-интерфейс модели ML PT-JPL",
        "input_params": "📝 Входные параметры",
        "select_area_method": "Выберите способ задания области:",
        "upload_shapefile": "Загрузить shapefile",
        "draw_polygon": "Нарисовать полигон на карте",
        "upload_file_prompt": "Загрузите shapefile (.zip (shp), .geojson, .gpkg)",
        "shapefile_loaded_zip": "✅ Shapefile загружен из ZIP: ",
        "geojson_loaded": "✅ GeoJSON загружен: ",
        "gpkg_loaded": "✅ GeoPackage загружен: ",
        "error_no_shp": "❌ В ZIP-архиве не найден файл .shp",
        "error_read_file": "❌ Ошибка чтения файла: ",
        "num_features": "📊 Количество объектов: ",
        "crs_label": "🗺️ Система координат: ",
        "polygon_drawn": "✅ Полигон успешно нарисован!",
        "polygon_loaded": "✅ Полигон загружен из сессии.",
        "date_range": "📅 Диапазон дат",
        "start_date": "Начальная дата",
        "end_date": "Конечная дата",
        "select_method": "Выберите метод",
        "method_help": "Выберите между ML PT-JPL и оригинальной моделью PT-JPL",
        "max_cloud": "Максимальная облачность (%)",
        "cloud_help": "Максимально допустимый процент облачности",
        "output_locations": "💾 Настройки вывода",
        "out_ptjpl_label": "Папка для сохранения снимков Landsat PT-JPL (временная)",
        "out_ptjpl_help": "Временный путь для выходных изображений PT-JPL",
        "out_meteo_label": "Путь для сохранения метеорологического файла ERA5-Land (временный)",
        "out_meteo_help": "Временный путь для метеоданных",
        "processing_results": "⚙️ Обработка и результаты",
        "current_config": "Текущая конфигурация",
        "config_start": "Начальная дата",
        "config_end": "Конечная дата",
        "config_method": "Метод",
        "config_cloud": "Макс. облачность",
        "config_out_ptjpl": "Выходные данные PT-JPL",
        "config_out_meteo": "Метеоданные",
        "run_button": "🚀 Запустить модель PT-JPL",
        "errors_upload": "Пожалуйста, загрузите shapefile",
        "errors_draw": "Пожалуйста, нарисуйте полигон на карте",
        "errors_dates": "Начальная дата должна быть раньше конечной",
        "errors_cloud": "Максимальная облачность должна быть от 0 до 100",
        "progress_complete": "✅ Обработка успешно завершена!",
        "results_header": "📊 Результаты",
        "success_message": "Обработка завершена! Используйте кнопки выше для скачивания результатов.",
        "error_processing": "❌ Ошибка во время обработки: ",
        "sidebar_instructions": "ℹ️ Инструкция",
        "sidebar_steps": """
        1. **Выберите способ задания области** – загрузите shapefile или нарисуйте полигон на карте (одно сельскохозяйственное поле)
        2. **Выберите диапазон дат** для анализа (не более одного года)
        3. **Выберите метод** (ML PT-JPL или оригинальный PT-JPL)
        4. **Установите максимальный процент облачности**
        5. **Нажмите «Запустить модель PT-JPL»**, чтобы начать обработку
        6. **Скачайте результаты**, используя появляющиеся после обработки кнопки
        """,
        "map_subheader": "Нарисуйте интересующую область",
        "map_background": "Выберите подложку карты:",
        "map_viewer": "🗺️ Просмотр карты",
        "shapefile_loaded_sidebar": "✅ Shapefile загружен: ",
        "shapefile_info": "Информация о shapefile",
        "crs": "СК: ",
        "features": "Объектов: ",
        "area": "Общая площадь: ",
        "sq_units": " кв. ед.",
        "tiff_folder_not_found": "Папка TIFF '{folder}' не найдена. Проверьте путь.",
        "no_tiff_files": "В папке '{folder}' не найдено файлов TIFF",
        "date_parse_error": "Не удалось распознать дату из имени файла: ",
        "no_valid_tiff": "Не найдено файлов TIFF с корректной датой в имени",
        "map_controls": "Управление картой",
        "select_date": "Выберите дату",
        "select_band": "Выберите канал",
        "status_info": "📅 Выбрано: {date}\n🎯 Канал: {band}/{total}",
        "map_subheader_date": "{date} \n **{band_label} - Канал {band}**",
        "cropping_spinner": "🔄 Обрезка TIFF по границе shapefile и создание карты...",
        "band_stats": "📊 Статистика канала (обрезанная область)",
        "min": "Мин",
        "max": "Макс",
        "mean": "Среднее",
        "std_dev": "Ст. откл.",
        "histogram_x": "Значение канала {band}",
        "histogram_y": "Частота",
        "histogram_title": "Гистограмма - {date} Канал {band}",
        "file_info": "ℹ️ Информация о файле",
        "file_name": "Файл: ",
        "original_crs": "Исходная СК: ",
        "original_bounds": "Исходные границы: ",
        "original_dims": "Исходные размеры: ",
        "num_bands": "Количество каналов: ",
        "data_type": "Тип данных: ",
        "nodata": "Значение NoData: ",
        "cropped_info": "Обрезано по области интереса:",
        "cropped_dims": "Размеры после обрезки: ",
        "cropped_bounds": "Границы после обрезки: ",
        "valid_pixels": "Валидных пикселей: ",
        "error_map": "❌ Ошибка создания карты: ",
        "map_info": "Убедитесь, что файл TIFF пересекается с shapefile и содержит корректные геопространственные данные.",
        "gee_init_failed": "❌ Ошибка инициализации GEE: ",
        "language_selector": "🌐 Язык / Language",
        "en": "English",
        "ru": "Русский",
        "download_all_tiffs": "📥 Скачать TIFF файлы",
        "download_meteo": "📥 Скачать метеоданные",
        "download_timeseries": "📥 Скачать временные ряды",
        "download_single_tiff": "📥 Скачать этот TIFF"
    }
}

def get_language():
    """Determine language from session state or browser preference."""
    if 'language' in st.session_state:
        return st.session_state.language
    try:
        query_params = st.query_params
        lang_param = query_params.get("lang", None)
        if lang_param in ["en", "ru"]:
            st.session_state.language = lang_param
            return lang_param
    except:
        pass
    try:
        browser_lang = st.context.headers.get("Accept-Language", "")
        if "ru" in browser_lang.lower():
            return "ru"
    except:
        pass
    return "en"

def set_language(lang):
    """Set language in session state."""
    st.session_state.language = lang

def _(key, **kwargs):
    """Return translation for given key with optional formatting."""
    lang = get_language()
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def initialize_gee(gee_project: str):
    """Initialize GEE using service account credentials from Streamlit secrets."""
    if st.session_state.get("gee_initialized"):
        return

    try:
        if "gee_service_account" in st.secrets:
            credentials_dict = dict(st.secrets["gee_service_account"])
            credentials = ee.ServiceAccountCredentials(
                email=credentials_dict["client_email"],
                key_data=json.dumps(credentials_dict)
            )
            ee.Initialize(credentials=credentials, project=gee_project)
        else:
            ee.Initialize(project=gee_project)
        st.session_state["gee_initialized"] = True
    except Exception as e:
        st.error(_("gee_init_failed") + str(e))
        st.stop()

BAND_NAMES = {
    1: "SR_B1 - Coastal/Aerosol",
    2: "SR_B2 - Blue",
    3: "SR_B3 - Green",
    4: "SR_B4 - Red",
    5: "SR_B5 - NIR",
    6: "SR_B6 - SWIR1",
    7: "SR_B7 - SWIR2",
    8: "ST_B10 - Thermal",
    9: "LE (Latent Heat Flux, W/m²)",
    10: "LEc (Canopy LE, W/m²)",
    11: "LEs (Soil LE, W/m²)",
    12: "ETrF (Evapotranspiration Fraction)",
    13: "LEc_ratio",
    14: "LEs_ratio",
    15: "IAVI (New Atmospherically Resistant Vegetation Index)",
    16: "GLI (Green Leaf Index)",
    17: "ExGR (Excess Green minus Red Index)",
    18: "SEVI (Shadow-Eliminated Vegetation Index)",
    19: "ET (Evapotranspiration, mm/day)",
    20: "ETc (Transpiration, mm/day)",
    21: "ETs (Soil evaporation, mm/day)"
}

def create_zip_download(tiff_folder):
    """Create a ZIP file of all TIFF files for download."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        tif_files = sorted(glob.glob(os.path.join(tiff_folder, "*.tif")))
        for tif_file in tif_files:
            zip_file.write(tif_file, os.path.basename(tif_file))
    zip_buffer.seek(0)
    return zip_buffer

def draw_polygon_map():
    """Create an interactive map for polygon drawing"""
    st.subheader(_("map_subheader"))

    if 'polygon_coords' not in st.session_state:
        st.session_state.polygon_coords = None

    tile_options = {
        "Google Hybrid": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        "Google Satellite": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        "OpenStreetMap": "OpenStreetMap",
    }

    selected = st.selectbox(_("map_background"), list(tile_options.keys()))

    m = folium.Map(
        location=[51.546516, 46.839902],
        zoom_start=13,
        tiles=tile_options[selected],
        attr="Google" if "google" in selected.lower() else None
    )

    draw_control = folium.plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polygon': {'allowIntersection': False,
                        'drawError': {'color': '#e1e100', 'message': 'Polygon cannot intersect!'}},
            'polyline': False,
            'circle': False,
            'rectangle': {'showArea': True},
            'marker': False,
            'circlemarker': False
        },
        edit_options={'edit': True, 'remove': True}
    )
    draw_control.add_to(m)

    output = st_folium(m, width=700, height=500)

    if output and output.get('last_active_drawing'):
        drawing = output['last_active_drawing']
        if drawing.get('geometry', {}).get('type') == 'Polygon':
            coords = drawing['geometry']['coordinates'][0]
            st.session_state.polygon_coords = coords
            return {
                'type': 'Polygon',
                'coordinates': coords,
                'geojson': drawing
            }
        elif drawing.get('geometry', {}).get('type') == 'Rectangle':
            coords = drawing['geometry']['coordinates'][0]
            st.session_state.polygon_coords = coords
            return {
                'type': 'Polygon',
                'coordinates': coords,
                'geojson': drawing
            }

    if st.session_state.polygon_coords:
        return {
            'type': 'Polygon',
            'coordinates': st.session_state.polygon_coords
        }
    return None

def save_drawn_polygon(drawn_data, output_path):
    """Save drawn polygon as shapefile"""
    if not drawn_data:
        return False

    if 'type' in drawn_data and drawn_data['type'] == 'Polygon':
        coords = drawn_data['coordinates']
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        from shapely.geometry import Polygon
        polygon = Polygon(coords)
        gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')
        gdf.to_file(output_path)
        return True
    elif 'geojson' in drawn_data:
        geojson_data = drawn_data['geojson']
        if 'geometry' in geojson_data and geojson_data['geometry']['type'] == 'Polygon':
            coords = geojson_data['geometry']['coordinates'][0]
            from shapely.geometry import Polygon
            polygon = Polygon(coords)
            gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')
            gdf.to_file(output_path)
            return True
    elif 'geometry' in drawn_data and drawn_data['geometry']['type'] == 'Polygon':
        coords = drawn_data['geometry']['coordinates'][0]
        from shapely.geometry import Polygon
        polygon = Polygon(coords)
        gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')
        gdf.to_file(output_path)
        return True
    return False

def get_tif_value(tif_path, shape_gdf):
    with rasterio.open(tif_path) as src:
        geom = shape_gdf.geometry.values[0]
        out_image, _mask = mask(src, [mapping(geom)], crop=True, nodata=np.nan)
        values = []
        for band in range(18, 21):
            band_data = out_image[band]
            valid = band_data[band_data > 0]
            values.append(np.nanmean(valid) if len(valid) > 0 else np.nan)
            values.append(np.std(valid) if len(valid) > 0 else np.nan)
        date_str = os.path.basename(tif_path).split('.')[0]
        return {
            'date': pd.to_datetime(date_str),
            'ET': values[0],
            'ET_std': values[1],
            'ETc': values[2],
            'ETc_std': values[3],
            'ETs': values[4],
            'ETs_std': values[5]
        }

def render_timeseries_plot(df, meteo_df):
    colors = {
        'ET': '#008080',
        'ETc': '#2EC767',
        'ETs': '#B58935',
        'ERA': '#E54522'
    }
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    window_length = min(17, len(df) - (len(df) % 2) - 1)
    if window_length < 3:
        window_length = 3
    polyorder = min(3, window_length - 1)
    
    df['ETc_smooth'] = savgol_filter(df['ETc'], window_length, polyorder)
    df['ETs_smooth'] = savgol_filter(df['ETs'], window_length, polyorder)
    df['ET_smooth'] = savgol_filter(df['ET'], window_length, polyorder)
    ax.plot(df['date'], df['ET'], color=colors['ET'], linewidth=1, linestyle='--', label='_nolegend_', alpha=0.9)
    ax.plot(df['date'], df['ETc'], color=colors['ETc'], linewidth=1, linestyle='--', label='_nolegend_', alpha=0.9)
    ax.plot(df['date'], df['ETs'], color=colors['ETs'], linewidth=1, linestyle='--', label='_nolegend_', alpha=0.9)
    ax.plot(df['date'], df['ET_smooth'], color=colors['ET'], linewidth=2, label='ET')
    ax.plot(df['date'], df['ETc_smooth'], color=colors['ETc'], linewidth=2, label='ETc')
    ax.plot(df['date'], df['ETs_smooth'], color=colors['ETs'], linewidth=2, label='ETs')
    if 'ETc_std' in df.columns:
        ax.fill_between(df['date'], df['ETc'] - df['ETc_std'], df['ETc'] + df['ETc_std'], color=colors['ETc'], alpha=0.2)
    if 'ETs_std' in df.columns:
        ax.fill_between(df['date'], df['ETs'] - df['ETs_std'], df['ETs'] + df['ETs_std'], color=colors['ETs'], alpha=0.2)
    if 'ET' in df.columns:
        ax.fill_between(df['date'], df['ET'] - df['ET_std'], df['ET'] + df['ET_std'], color=colors['ET'], alpha=0.2)
    meteo_df['ETr_24_ERA_smooth'] = savgol_filter(meteo_df['ETr_24_ERA'], window_length, polyorder)
    ax.plot(meteo_df['Date'], meteo_df['ETr_24_ERA'], color=colors['ERA'], linewidth=1, linestyle='--', alpha=0.9, label='_nolegend_')
    ax.plot(meteo_df['Date'], meteo_df['ETr_24_ERA_smooth'], color=colors['ERA'], linewidth=2, label='ETr')
    ax.set_ylabel('mm/day', fontsize=14)
    ax.set_xlabel('Date', fontsize=14)
    ax.set_title('ET — actual evapotranspiration, ETc — transpiration \n ETs —  soil evaporation, ETr — reference ET', fontsize=16, pad=15)
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=12)
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    ax.tick_params(axis='x', rotation=45, labelsize=12)
    ax.tick_params(axis='y', labelsize=12)
    min_date = min(df['date'].min(), meteo_df['Date'].min())
    max_date = max(df['date'].max(), meteo_df['Date'].max())
    ax.set_xlim([min_date, max_date])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

def crop_tiff_to_shape(tiff_path, shape_gdf):
    with rasterio.open(tiff_path) as src:
        if shape_gdf.crs != src.crs:
            shape_gdf = shape_gdf.to_crs(src.crs)
        geoms = [mapping(shape_gdf.geometry.unary_union)]
        out_image, out_transform = mask(src, geoms, crop=True, nodata=np.nan)
        bounds = rasterio.transform.array_bounds(out_image.shape[1], out_image.shape[2], out_transform)
        return out_image, out_transform, bounds

def create_map_with_cropped_tiff(tiff_path, band_idx=19, shape_gdf=None):
    cropped_data, transform, bounds = crop_tiff_to_shape(tiff_path, shape_gdf)
    band_data = cropped_data[band_idx - 1]
    valid_data = band_data[~np.isnan(band_data)]
    if len(valid_data) > 0:
        band_min = np.nanpercentile(valid_data, 2)
        band_max = np.nanpercentile(valid_data, 98)
    else:
        band_min, band_max = 0, 1
    band_normalized = np.clip((band_data - band_min) / (band_max - band_min) * 255, 0, 255)
    band_normalized = np.nan_to_num(band_normalized, nan=0).astype(np.uint8)
    colormap = plt.cm.RdYlBu
    colored_band = colormap(band_normalized / 255.0)
    alpha_channel = np.where(band_normalized > 0, 0.8, 0.0)
    colored_band = np.dstack([(colored_band[:, :, :3] * 255).astype(np.uint8), (alpha_channel * 255).astype(np.uint8)])
    img = Image.fromarray(colored_band, mode='RGBA')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
    shape_gdf_4326 = shape_gdf.to_crs('EPSG:4326')
    center_4326 = [(shape_gdf_4326.total_bounds[1] + shape_gdf_4326.total_bounds[3]) / 2,
                   (shape_gdf_4326.total_bounds[0] + shape_gdf_4326.total_bounds[2]) / 2]
    m = folium.Map(location=center_4326, zoom_start=14, control_scale=True)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Hybrid', overlay=False, control=True).add_to(m)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite', overlay=False, control=True).add_to(m)
    bounds_4326 = [[shape_gdf_4326.total_bounds[1], shape_gdf_4326.total_bounds[0]],
                   [shape_gdf_4326.total_bounds[3], shape_gdf_4326.total_bounds[2]]]
    colors = ['#313695', '#74add1', '#ffffbf', '#f46d43', '#a50026']
    reversed_colors = colors[::-1]
    if len(valid_data) > 0:
        colormap_legend = cm.LinearColormap(colors=reversed_colors, vmin=band_min, vmax=band_max, text_color='white', caption='')
        m.add_child(colormap_legend)
    image_overlay = folium.raster_layers.ImageOverlay(image=f'data:image/png;base64,{img_base64}', bounds=bounds_4326, opacity=0.85, name=f'Band {band_idx} Overlay', interactive=True, cross_origin=False, zindex=2)
    image_overlay.add_to(m)
    folium.GeoJson(shape_gdf_4326, name='Area Boundary', style_function=lambda x: {'fillColor': '#000000', 'color': '#ffffff', 'weight': 2, 'fillOpacity': 0.0, 'dashArray': '5, 5'}).add_to(m)
    folium.LayerControl().add_to(m)
    plugins.Fullscreen().add_to(m)
    plugins.Draw(export=False, filename='measurements.geojson', position='topleft', draw_options={'polyline': {'shapeOptions': {'color': '#ff0000', 'weight': 3}}, 'polygon': {'shapeOptions': {'color': '#00ff00', 'weight': 2, 'fillOpacity': 0.2}}, 'rectangle': {'shapeOptions': {'color': '#0000ff', 'weight': 2, 'fillOpacity': 0.2}}, 'circle': False, 'marker': True, 'circlemarker': False}, edit_options={'edit': True, 'remove': True}).add_to(m)
    return m, valid_data

def results_section(tiff_folder, shape_file):
    st.header(_("map_viewer"))
    if not os.path.exists(shape_file):
        st.error(_("tiff_folder_not_found", folder=shape_file))
        return
    try:
        shape_gdf = gpd.read_file(shape_file)
        original_crs = shape_gdf.crs
        shape_gdf = shape_gdf.to_crs('EPSG:4326')
        st.sidebar.success(_("shapefile_loaded_sidebar") + str(len(shape_gdf)))
        with st.sidebar.expander(_("shapefile_info")):
            st.write(f"**{_('crs')}** {original_crs}")
            st.write(f"**{_('features')}** {len(shape_gdf)}")
            st.write(f"**{_('area')}** {shape_gdf.to_crs(original_crs).area.sum():.2f}{_('sq_units')}")
    except Exception as e:
        st.error(_("error_read_file") + str(e))
        return
    if not os.path.exists(tiff_folder):
        st.error(_("tiff_folder_not_found", folder=tiff_folder))
        return
    tif_files = sorted(glob.glob(os.path.join(tiff_folder, "*.tif")))
    if not tif_files:
        st.warning(_("no_tiff_files", folder=tiff_folder))
        return
    dates = []
    for tif_file in tif_files:
        filename = os.path.basename(tif_file)
        date_str = filename.replace('.tif', '').replace('.tiff', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            dates.append((date_obj, date_str, tif_file))
        except:
            st.warning(_("date_parse_error") + filename)
    if not dates:
        st.error(_("no_valid_tiff"))
        return
    dates.sort(key=lambda x: x[0])
    st.sidebar.header(_("map_controls"))
    date_options = [f"{d[0].strftime('%Y-%m-%d')}" for d in dates]
    selected_date_idx = st.sidebar.selectbox(_("select_date"), range(len(date_options)), format_func=lambda x: date_options[x], index=len(date_options)-1)
    selected_tiff = dates[selected_date_idx][2]
    
    # Add download button for current TIFF
    with open(selected_tiff, 'rb') as f:
        st.sidebar.download_button(
            label=_("download_single_tiff"),
            data=f,
            file_name=os.path.basename(selected_tiff),
            mime="image/tiff",
            key=f"download_tiff_{selected_date_idx}"
        )
    
    with rasterio.open(selected_tiff) as src:
        num_bands = src.count
    default_band_idx = 18 if num_bands >= 19 else 0
    band_options = [f"Band {i+1} - {BAND_NAMES[i+1]}" if (i+1) in BAND_NAMES else f"Band {i+1}" for i in range(num_bands)]
    selected_band_idx = st.sidebar.selectbox(_("select_band"), range(len(band_options)), format_func=lambda x: band_options[x], index=min(default_band_idx, num_bands-1))
    selected_band = selected_band_idx + 1
    st.sidebar.info(_("status_info", date=date_options[selected_date_idx], band=selected_band, total=num_bands))
    band_label = BAND_NAMES.get(selected_band, f"Band {selected_band}")
    st.subheader(_("map_subheader_date", date=date_options[selected_date_idx], band_label=band_label, band=selected_band))
    try:
        with st.spinner(_("cropping_spinner")):
            folium_map, valid_data = create_map_with_cropped_tiff(tiff_path=selected_tiff, band_idx=selected_band, shape_gdf=shape_gdf)
            st_folium(folium_map, width=None, height=400, returned_objects=[], key=f"result_map_{selected_date_idx}_{selected_band_idx}")
        with st.expander(_("band_stats")):
            if len(valid_data) > 0:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(_("min"), f"{np.nanmin(valid_data):.2f}")
                with col2:
                    st.metric(_("max"), f"{np.nanmax(valid_data):.2f}")
                with col3:
                    st.metric(_("mean"), f"{np.nanmean(valid_data):.2f}")
                with col4:
                    st.metric(_("std_dev"), f"{np.nanstd(valid_data):.2f}")
                fig, ax = plt.subplots(figsize=(10, 3))
                ax.hist(valid_data, bins=50, edgecolor='black', alpha=0.7)
                ax.set_xlabel(_("histogram_x", band=selected_band))
                ax.set_ylabel(_("histogram_y"))
                ax.set_title(_("histogram_title", date=date_options[selected_date_idx], band=selected_band))
                ax.grid(True, alpha=0.3)
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.warning("No valid data in cropped area")
        with st.expander(_("file_info")):
            with rasterio.open(selected_tiff) as src:
                st.write(f"**{_('file_name')}** {os.path.basename(selected_tiff)}")
                st.write(f"**{_('original_crs')}** {src.crs}")
                st.write(f"**{_('original_bounds')}** {src.bounds}")
                st.write(f"**{_('original_dims')}** {src.width} x {src.height}")
                st.write(f"**{_('num_bands')}** {src.count}")
                st.write(f"**{_('data_type')}** {src.dtypes[0]}")
                st.write(f"**{_('nodata')}** {src.nodata}")
                st.write("---")
                st.write(f"**{_('cropped_info')}**")
                cropped_data, _transform, bounds = crop_tiff_to_shape(selected_tiff, shape_gdf)
                st.write(f"**{_('cropped_dims')}** {cropped_data.shape[2]} x {cropped_data.shape[1]}")
                st.write(f"**{_('cropped_bounds')}** {bounds}")
                st.write(f"**{_('valid_pixels')}** {np.sum(~np.isnan(cropped_data[selected_band - 1]))}")
    except Exception as e:
        st.error(_("error_map") + str(e))
        st.info(_("map_info"))


def main():
    st.set_page_config(page_title=_("page_title"), page_icon=_("page_icon"), layout="wide")
    with st.sidebar:
        lang = st.selectbox(_("language_selector"), options=["en", "ru"],
                            format_func=lambda x: TRANSLATIONS[x]["en" if x == "en" else "ru"],
                            index=0 if get_language() == "en" else 1, key="language_selector_widget")
        if lang != st.session_state.get('language'):
            set_language(lang)
            st.rerun()
    initialize_gee(gee_project="ee-dobralexey")
    col1, col2 = st.columns([1, 0.2])
    with col2:
        st.image("logo.png", width=100)
    with col1:
        st.title(_("title"))
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.header(_("input_params"))
        input_method = st.radio(_("select_area_method"), [_("upload_shapefile"), _("draw_polygon")])
        # shape_path and shp_file are always resolved from session_state so they
        # survive the rerun that Streamlit triggers when any button is clicked.
        shape_path = st.session_state.get('_shape_path')
        shp_file   = st.session_state.get('_shp_file')
        drawn_polygon = st.session_state.get('drawn_polygon_data')
        gdf = None

        if input_method == _("upload_shapefile"):
            # Clear drawn-polygon state when switching to upload mode
            st.session_state.pop('drawn_polygon_data', None)
            drawn_polygon = None

            uploaded_file = st.file_uploader(_("upload_file_prompt"), type=['geojson', 'zip', 'gpkg'])
            if uploaded_file is not None:
                # Identify this upload by name+size; only re-process when it's new
                upload_key = f"{uploaded_file.name}_{uploaded_file.size}"
                if st.session_state.get('_upload_key') != upload_key:
                    # New file: write to a persistent temp dir and store paths in session_state
                    old_dir = st.session_state.get('_upload_tmp_dir')
                    if old_dir and os.path.isdir(old_dir):
                        shutil.rmtree(old_dir, ignore_errors=True)
                    tmp_dir = tempfile.mkdtemp(prefix='agroet_upload_')
                    st.session_state['_upload_tmp_dir'] = tmp_dir
                    tmp_path = os.path.join(tmp_dir, uploaded_file.name)
                    with open(tmp_path, 'wb') as f:
                        f.write(uploaded_file.getbuffer())
                    try:
                        if uploaded_file.name.endswith('.zip'):
                            extract_dir = os.path.join(tmp_dir, 'extracted')
                            os.makedirs(extract_dir, exist_ok=True)
                            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                                zip_ref.extractall(extract_dir)
                            found_shp = None
                            for file in os.listdir(extract_dir):
                                if file.endswith('.shp'):
                                    found_shp = os.path.join(extract_dir, file)
                                    break
                            if found_shp is None:
                                st.error(_("error_no_shp"))
                                st.session_state.pop('_upload_key', None)
                                st.session_state.pop('_shape_path', None)
                                st.session_state.pop('_shp_file', None)
                            else:
                                gdf = gpd.read_file(found_shp)
                                st.session_state['_upload_key']  = upload_key
                                st.session_state['_shape_path']  = found_shp
                                st.session_state['_shp_file']    = found_shp
                                st.session_state['_gdf_nfeat']   = len(gdf)
                                st.session_state['_gdf_crs']     = str(gdf.crs)
                        elif uploaded_file.name.endswith('.geojson'):
                            gdf = gpd.read_file(tmp_path)
                            st.session_state['_upload_key']  = upload_key
                            st.session_state['_shape_path']  = tmp_path
                            st.session_state['_shp_file']    = tmp_path
                            st.session_state['_gdf_nfeat']   = len(gdf)
                            st.session_state['_gdf_crs']     = str(gdf.crs)
                        elif uploaded_file.name.endswith('.gpkg'):
                            gdf = gpd.read_file(tmp_path)
                            st.session_state['_upload_key']  = upload_key
                            st.session_state['_shape_path']  = tmp_path
                            st.session_state['_shp_file']    = tmp_path
                            st.session_state['_gdf_nfeat']   = len(gdf)
                            st.session_state['_gdf_crs']     = str(gdf.crs)
                    except Exception as e:
                        st.error(_("error_read_file") + str(e))
                        st.session_state.pop('_upload_key', None)
                        st.session_state.pop('_shape_path', None)
                        st.session_state.pop('_shp_file', None)

                # Always refresh local vars from session_state (covers the rerun-after-click case)
                shape_path = st.session_state.get('_shape_path')
                shp_file   = st.session_state.get('_shp_file')

                if shape_path:
                    if uploaded_file.name.endswith('.zip'):
                        st.success(_("shapefile_loaded_zip") + os.path.basename(shape_path))
                    elif uploaded_file.name.endswith('.geojson'):
                        st.success(_("geojson_loaded") + uploaded_file.name)
                    elif uploaded_file.name.endswith('.gpkg'):
                        st.success(_("gpkg_loaded") + uploaded_file.name)
                    st.write(_("num_features") + str(st.session_state.get('_gdf_nfeat', '')))
                    st.write(_("crs_label") + str(st.session_state.get('_gdf_crs', '')))
            else:
                # File uploader cleared — wipe persisted state
                for k in ['_upload_key', '_shape_path', '_shp_file', '_gdf_nfeat', '_gdf_crs']:
                    st.session_state.pop(k, None)
                shape_path = None
                shp_file   = None

        else:
            # Draw polygon mode — clear upload state
            for k in ['_upload_key', '_shape_path', '_shp_file', '_gdf_nfeat', '_gdf_crs']:
                st.session_state.pop(k, None)
            shape_path = None
            shp_file   = None

            drawn_polygon = draw_polygon_map()
            if drawn_polygon:
                st.success(_("polygon_drawn"))
                st.session_state['drawn_polygon_data'] = drawn_polygon
            elif st.session_state.get('drawn_polygon_data'):
                drawn_polygon = st.session_state['drawn_polygon_data']
                st.success(_("polygon_loaded"))
        st.subheader(_("date_range"))
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            start_date = st.date_input(_("start_date"), value=date(2024, 7, 1), min_value=date(2013, 1, 1),
                                       max_value=date(2050, 12, 31))
        with col_date2:
            end_date = st.date_input(_("end_date"), value=date(2024, 7, 31), min_value=date(2013, 1, 1),
                                     max_value=date(2050, 12, 31))
        method = st.selectbox(_("select_method"), options=['ML PT-JPL', 'Original PT-JPL'], help=_("method_help"))
        max_cloud = st.slider(_("max_cloud"), min_value=0, max_value=100, value=20, step=5, help=_("cloud_help"))

    with col2:
        st.header(_("processing_results"))
        st.subheader(_("current_config"))
        config_data = {
            _("config_start"): start_date,
            _("config_end"): end_date,
            _("config_method"): method,
            _("config_cloud"): f"{max_cloud}%",
        }
        for key, value in config_data.items():
            st.text(f"{key}: {value}")
        st.markdown("---")
        run_button = st.button(_("run_button"), type="primary", use_container_width=True)
        if run_button:
            # Re-read from session_state in case the rerun reset local vars
            if not shape_path and input_method == _("upload_shapefile"):
                shape_path = st.session_state.get('_shape_path')
                shp_file   = st.session_state.get('_shp_file')
            if not drawn_polygon and input_method == _("draw_polygon"):
                drawn_polygon = st.session_state.get('drawn_polygon_data')

            errors = []
            if input_method == _("upload_shapefile") and not shape_path:
                errors.append(_("errors_upload"))
            elif input_method == _("draw_polygon") and not drawn_polygon:
                errors.append(_("errors_draw"))
            if start_date > end_date:
                errors.append(_("errors_dates"))
            if max_cloud < 0 or max_cloud > 100:
                errors.append(_("errors_cloud"))
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                temp_shape_path = None
                shp_file = shp_file or shape_path  # ensure always defined
                if input_method == _("draw_polygon") and drawn_polygon:
                    temp_shape_dir = tempfile.mkdtemp(prefix='agroet_drawn_')
                    temp_shape_path = os.path.join(temp_shape_dir, 'drawn_polygon.shp')
                    save_drawn_polygon(drawn_polygon, temp_shape_path)
                    shape_path = temp_shape_path
                    shp_file = shape_path
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(percent, message):
                    progress_bar.progress(percent)
                    status_text.text(f"{message} ({percent}%)")

                try:
                    start_date_str = start_date.strftime('%Y-%m-%d')
                    end_date_str = end_date.strftime('%Y-%m-%d')

                    # Create temporary directories for outputs ONLY when running
                    temp_output_dir = tempfile.mkdtemp(prefix='agroet_output_')
                    out_ptjpl = os.path.join(temp_output_dir, 'images')
                    out_meteo = os.path.join(temp_output_dir, 'meteo', 'meteo.feather')
                    os.makedirs(out_ptjpl, exist_ok=True)
                    os.makedirs(os.path.dirname(out_meteo), exist_ok=True)

                    # Clean up old temp dir if exists
                    if 'temp_output_dir' in st.session_state:
                        try:
                            shutil.rmtree(st.session_state.temp_output_dir, ignore_errors=True)
                        except:
                            pass
                    st.session_state.temp_output_dir = temp_output_dir

                    run_et_calculation(shape_path=shape_path, start_date=start_date_str, end_date=end_date_str,
                                       method=method, max_cloud=max_cloud, out_ptjpl=out_ptjpl, out_meteo=out_meteo,
                                       progress_callback=update_progress)
                    status_text.text(_("progress_complete"))

                    persistent_shp_dir = tempfile.mkdtemp(prefix='agroet_persistent_')
                    persistent_shp_path = os.path.join(persistent_shp_dir, os.path.basename(shp_file))
                    shutil.copy2(shp_file, persistent_shp_path)
                    shp_base = os.path.splitext(shp_file)[0]
                    for ext in ['.dbf', '.shx', '.prj', '.cpg', '.qpj']:
                        src_side = shp_base + ext
                        if os.path.exists(src_side):
                            shutil.copy2(src_side, os.path.join(persistent_shp_dir, os.path.basename(src_side)))
                    old_dir = st.session_state.get('results_shp_persistent_dir')
                    if old_dir and os.path.exists(old_dir) and old_dir != persistent_shp_dir:
                        shutil.rmtree(old_dir, ignore_errors=True)
                    st.session_state['results_tiff_folder'] = out_ptjpl
                    st.session_state['results_shp_file'] = persistent_shp_path
                    st.session_state['results_shp_persistent_dir'] = persistent_shp_dir
                    st.session_state['results_meteo_file'] = out_meteo

                    st.subheader(_("results_header"))

                    # Add download buttons for all results
                    col_down1, col_down2, col_down3 = st.columns(3)
                    with col_down1:
                        if os.path.exists(out_ptjpl) and glob.glob(os.path.join(out_ptjpl, "*.tif")):
                            zip_buffer = create_zip_download(out_ptjpl)
                            st.download_button(
                                label=_("download_all_tiffs"),
                                data=zip_buffer,
                                file_name=f"pt_jpl_results_{start_date_str}_{end_date_str}.zip",
                                mime="application/zip"
                            )

                    with col_down2:
                        if os.path.exists(out_meteo):
                            with open(out_meteo, 'rb') as f:
                                st.download_button(
                                    label=_("download_meteo"),
                                    data=f,
                                    file_name=f"meteo_data_{start_date_str}_{end_date_str}.feather",
                                    mime="application/octet-stream"
                                )

                    shape_gdf = gpd.read_file(shp_file)
                    shape_gdf = shape_gdf.to_crs('EPSG:4326')
                    tif_files = sorted(glob.glob(os.path.join(out_ptjpl, "*.tif")))
                    data = []
                    for tif in tif_files:
                        val = get_tif_value(tif, shape_gdf)
                        if val:
                            data.append(val)
                    df = pd.DataFrame(data).sort_values('date')
                    meteo_df = pd.read_feather(out_meteo)
                    meteo_df['Date'] = pd.to_datetime(meteo_df['Date'])

                    with col_down3:
                        # Create CSV of timeseries data
                        csv_buffer = io.StringIO()
                        combined_df = df.merge(meteo_df, left_on='date', right_on='Date', how='outer')
                        combined_df.to_csv(csv_buffer, index=False)
                        st.download_button(
                            label=_("download_timeseries"),
                            data=csv_buffer.getvalue(),
                            file_name=f"timeseries_data_{start_date_str}_{end_date_str}.csv",
                            mime="text/csv"
                        )

                    st.session_state['results_df'] = df
                    st.session_state['results_meteo_df'] = meteo_df
                    render_timeseries_plot(df, meteo_df)
                    results_section(out_ptjpl, persistent_shp_path)
                    st.success(_("success_message"))
                except Exception as e:
                    st.error(_("error_processing") + str(e))
                finally:
                    if temp_shape_path and os.path.exists(os.path.dirname(temp_shape_path)):
                        shutil.rmtree(os.path.dirname(temp_shape_path), ignore_errors=True)
                    if shape_path and input_method == _("upload_shapefile") and os.path.exists(shape_path):
                        shutil.rmtree(os.path.dirname(shape_path), ignore_errors=True)

        # Display results if they exist in session state
        if not run_button and 'results_tiff_folder' in st.session_state and 'results_shp_file' in st.session_state:
            # Check if the results folder still exists
            if os.path.exists(st.session_state.results_tiff_folder):
                st.subheader(_("results_header"))

                # Add download buttons for existing results
                if 'results_tiff_folder' in st.session_state and 'results_meteo_file' in st.session_state:
                    col_down1, col_down2, col_down3 = st.columns(3)
                    with col_down1:
                        tiff_folder = st.session_state.results_tiff_folder
                        if os.path.exists(tiff_folder) and glob.glob(os.path.join(tiff_folder, "*.tif")):
                            zip_buffer = create_zip_download(tiff_folder)
                            st.download_button(
                                label=_("download_all_tiffs"),
                                data=zip_buffer,
                                file_name="pt_jpl_results.zip",
                                mime="application/zip"
                            )

                    with col_down2:
                        meteo_file = st.session_state.results_meteo_file
                        if os.path.exists(meteo_file):
                            with open(meteo_file, 'rb') as f:
                                st.download_button(
                                    label=_("download_meteo"),
                                    data=f,
                                    file_name="meteo_data.feather",
                                    mime="application/octet-stream"
                                )

                    with col_down3:
                        if 'results_df' in st.session_state and 'results_meteo_df' in st.session_state:
                            csv_buffer = io.StringIO()
                            combined_df = st.session_state.results_df.merge(
                                st.session_state.results_meteo_df,
                                left_on='date',
                                right_on='Date',
                                how='outer'
                            )
                            combined_df = combined_df.drop(columns='Date')
                            combined_df.to_csv(csv_buffer, index=False)
                            st.download_button(
                                label=_("download_timeseries"),
                                data=csv_buffer.getvalue(),
                                file_name="timeseries_data.csv",
                                mime="text/csv"
                            )

                if 'results_df' in st.session_state and 'results_meteo_df' in st.session_state:
                    render_timeseries_plot(st.session_state['results_df'], st.session_state['results_meteo_df'])
                results_section(st.session_state['results_tiff_folder'], st.session_state['results_shp_file'])
            else:
                st.warning(_("tiff_folder_not_found", folder=st.session_state.results_tiff_folder))
                # Clear invalid session state
                for key in ['results_tiff_folder', 'results_shp_file', 'results_meteo_file', 'results_df',
                            'results_meteo_df']:
                    if key in st.session_state:
                        del st.session_state[key]

    with st.sidebar:
        st.header(_("sidebar_instructions"))
        st.markdown(_("sidebar_steps"))

if __name__ == '__main__':
    main()