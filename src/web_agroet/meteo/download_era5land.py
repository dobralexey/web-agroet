import os
import ee
import pyet
import numpy as np
import pandas as pd

from src.web_agroet.meteo.meteo_utils import relative_humidity


ERA5LAND_DAILY_COLLECTION = 'ECMWF/ERA5_LAND/DAILY_AGGR'

def get_era5land(geometry, start_date, end_date):
    """
    Get ERA5-Land daily aggregated data for a geometry from GEE

    Parameters:
    -----------
    geometry :  geometry of the station
    start_date : str or datetime
        Start date (YYYY-MM-DD)
    end_date : str or datetime
        End date (YYYY-MM-DD)

    Returns:
    --------
    pandas.DataFrame
        Daily meteorological data
    """

    # Create ee.Geometry.Point from the geometry

    lon, lat = geometry.x[0], geometry.y[0]
    point = ee.Geometry.Point(lon, lat)

    end_date = pd.to_datetime(end_date) + pd.Timedelta(days=1)
    end_date = end_date.strftime('%Y-%m-%d')

    # Load ERA5-Land dataset
    era5 = ee.ImageCollection(ERA5LAND_DAILY_COLLECTION) \
        .filterDate(start_date, end_date) \
        .filterBounds(point)

    def extract_values(image):
        # Get date from image
        date = ee.Date(image.get('system:time_start'))
        date_str = date.format('YYYY-MM-dd')

        # Extract values for each variable
        def extract_var(var):
            value = image.select(var).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=point,
                scale=11132,
                bestEffort=True
            ).get(var)
            return value

        # Create a feature with all variables
        feature = ee.Feature(point, {
            'date': date_str,
            'temperature_2m': extract_var('temperature_2m'),
            'temperature_2m_min': extract_var('temperature_2m_min'),
            'temperature_2m_max': extract_var('temperature_2m_max'),
            'dewpoint_temperature_2m': extract_var('dewpoint_temperature_2m'),
            'surface_pressure': extract_var('surface_pressure'),
            'total_precipitation_sum': extract_var('total_precipitation_sum'),
            'surface_solar_radiation_downwards_sum': extract_var('surface_solar_radiation_downwards_sum'),
            'surface_net_solar_radiation_sum': extract_var('surface_net_solar_radiation_sum'),
            'surface_net_thermal_radiation_sum': extract_var('surface_net_thermal_radiation_sum'),
            'u_component_of_wind_10m': extract_var('u_component_of_wind_10m'),
            'v_component_of_wind_10m': extract_var('v_component_of_wind_10m'),
        })

        return feature

    features = era5.map(extract_values)

    data = features.getInfo()

    records = []
    for feature in data['features']:
        props = feature['properties']
        records.append({
            'date': props['date'],
            'temperature_2m': props['temperature_2m'],
            'temperature_2m_min': props['temperature_2m_min'],
            'temperature_2m_max': props['temperature_2m_max'],
            'dewpoint_temperature_2m': props['dewpoint_temperature_2m'],
            'surface_pressure': props['surface_pressure'],
            'total_precipitation_sum': props['total_precipitation_sum'],
            'surface_solar_radiation_downwards_sum': props['surface_solar_radiation_downwards_sum'],
            'surface_net_solar_radiation_sum': props['surface_net_solar_radiation_sum'],
            'surface_net_thermal_radiation_sum': props['surface_net_thermal_radiation_sum'],
            'u_component_of_wind_10m': props['u_component_of_wind_10m'],
            'v_component_of_wind_10m': props['v_component_of_wind_10m'],
        })

    df_era5 = pd.DataFrame(records)
    return df_era5

def transform_era5land(df_era5):

    df = df_era5.copy()

    df['Date'] = pd.to_datetime(df['date'])
    df['Tmean'] = df['temperature_2m'] - 273.15
    df['Tmin'] = df['temperature_2m_min'] - 273.15
    df['Tmax'] = df['temperature_2m_max'] - 273.15
    df['RH'] = df.apply(lambda row: relative_humidity(row['temperature_2m'], row['dewpoint_temperature_2m']),axis=1)
    df['Pres'] = df['surface_pressure']*0.001
    df['Rain'] = df['total_precipitation_sum'] * 1000
    df.loc[df['Rain'] < 1, 'Rain'] = 0
    df['RS'] = df['surface_solar_radiation_downwards_sum'] * 1e-6
    df['RNS'] = df['surface_net_solar_radiation_sum'] * 1e-6
    df['RNL'] = df['surface_net_thermal_radiation_sum'] * 1e-6
    df['Wind'] = np.sqrt(df['u_component_of_wind_10m'] ** 2 + df['v_component_of_wind_10m'] ** 2)
    df['Wind'] = df['Wind'] * (4.87 / (np.log(67.8 * 10 - 5.42)))

    df['Tmean'] = df['Tmean'].round(1)
    df['Tmin'] = df['Tmin'].round(1)
    df['Tmax'] = df['Tmax'].round(1)
    df['Pres'] = df['Pres'].round(2)
    df['RH'] = df['RH'].round(0)
    df['Rain'] = df['Rain'].round(1)
    df['RS'] = df['RS'].round(2)
    df['RNS'] = df['RNS'].round(2)
    df['RNL'] = df['RNL'].round(2)
    df['Wind'] = df['Wind'].round(1)

    df = df[['Date', 'Tmean', 'Tmin', 'Tmax', 'RH', 'Pres', 'Rain', 'RS', 'RNS', 'RNL', 'Wind']]
    df = df.sort_values('Date').reset_index(drop=True)

    return df

def calculate_reference_et(df_era5):
    df = df_era5.copy()
    df['RN'] = df['RNS'] + df['RNL']
    df['ETr_24_ERA'] = pyet.pm_asce(tmean=df['Tmean'],
                                    wind=df['Wind'],
                                    rn=df['RN'],
                                    tmax=df['Tmax'],
                                    tmin=df['Tmin'],
                                    rh=df['RH'],
                                    pressure=df['Pres'],
                                    etype='os')
    df['ETr_24_ERA'] = df['ETr_24_ERA'].round(2)
    df['ETr_24_ERA'] = df['ETr_24_ERA'].clip(0, 10)
    return df

def process_era5land(geometry, start_date, end_date, save=True, output_path='./data/daily_meteo.feather'):


    df = get_era5land(geometry, start_date, end_date)
    df = transform_era5land(df)
    df = calculate_reference_et(df)

    if save:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_feather(output_path)


    return df





