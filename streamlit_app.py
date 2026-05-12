import io
import os
import glob
import shutil
import zipfile
import tempfile
import pandas as pd
import geopandas as gpd
import streamlit as st
from datetime import date
from src.web_agroet.main import run_et_calculation
from app_translation import TRANSLATIONS
from app_functions import (get_language, set_language, initialize_gee, create_zip_download, draw_polygon_map,
                           save_drawn_polygon, get_tif_value, render_timeseries_plot, results_section)


def _(key, **kwargs):
    """Return translation for given key with optional formatting."""
    lang = get_language()
    text = TRANSLATIONS[lang].get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text

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
        shape_path = None
        drawn_polygon = None
        gdf = None
        if input_method == _("upload_shapefile"):
            uploaded_file = st.file_uploader(_("upload_file_prompt"), type=['geojson', 'zip', 'gpkg'])
            if uploaded_file:
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                try:
                    if uploaded_file.name.endswith('.zip'):
                        extract_dir = os.path.join(temp_dir, 'extracted')
                        os.makedirs(extract_dir, exist_ok=True)
                        with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        shp_file = None
                        for file in os.listdir(extract_dir):
                            if file.endswith('.shp'):
                                shp_file = os.path.join(extract_dir, file)
                                break
                        if shp_file is None:
                            st.error(_("error_no_shp"))
                        else:
                            gdf = gpd.read_file(shp_file)
                            shape_path = shp_file
                            st.success(_("shapefile_loaded_zip") + os.path.basename(shp_file))
                    elif uploaded_file.name.endswith('.geojson'):
                        gdf = gpd.read_file(temp_path)
                        shape_path = temp_path
                        shp_file = shape_path
                        st.success(_("geojson_loaded") + uploaded_file.name)
                    elif uploaded_file.name.endswith('.gpkg'):
                        gdf = gpd.read_file(temp_path)
                        shape_path = temp_path
                        shp_file = shape_path
                        st.success(_("gpkg_loaded") + uploaded_file.name)
                except Exception as e:
                    st.error(_("error_read_file") + str(e))
                    gdf = None
                    shape_path = None
                if gdf is not None:
                    st.write(_("num_features") + str(len(gdf)))
                    st.write(_("crs_label") + str(gdf.crs))
        else:
            drawn_polygon = draw_polygon_map()
            if drawn_polygon:
                st.success(_("polygon_drawn"))
                st.session_state['drawn_polygon_data'] = drawn_polygon
            elif 'drawn_polygon_data' in st.session_state:
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