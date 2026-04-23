import numpy as np
import rasterio
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from scipy.interpolate import interp1d
import warnings

warnings.filterwarnings('ignore')

DEFAULT_BAND_MAPPING = {
    'SR_B1': 1,
    'SR_B2': 2,
    'SR_B3': 3,
    'SR_B4': 4,
    'SR_B5': 5,
    'SR_B6': 6,
    'SR_B7': 7,
    'ST_B10': 9,
    'LE': 41,
    'LEc': 42,
    'LEs': 43,
    'ETrF': 50
}


def parse_date_from_filename(filename):
    """Extract date from filename (assuming YYYYMMDD format)"""
    import re
    match = re.search(r'(\d{8})', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d')
    return None


def filter_clouds(tif_path, cloud_band_index=23):
    """
    Filter cloud pixels where cloud_cover band > 0 is cloudy
    Returns mask where True = clear pixel, False = cloudy
    """
    with rasterio.open(tif_path) as src:
        cloud_band = src.read(cloud_band_index)
        clear_mask = cloud_band <= 0
    return clear_mask


def extract_bands(tif_path, band_indices):
    """Extract specified bands from TIF file"""
    with rasterio.open(tif_path) as src:
        bands_data = []
        for band_idx in band_indices:
            if band_idx <= src.count:
                band = src.read(band_idx)
                bands_data.append(band)
            else:
                print(f"Warning: Band {band_idx} not found in {tif_path}")
                bands_data.append(None)
    return bands_data


def apply_cloud_mask(bands_data, cloud_mask):
    """Apply cloud mask to bands (set cloudy pixels to NaN)"""
    masked_bands = []
    for band in bands_data:
        if band is not None:
            band_masked = band.astype(np.float32)
            band_masked[~cloud_mask] = np.nan
            masked_bands.append(band_masked)
        else:
            masked_bands.append(None)
    return masked_bands


def interpolate_band(all_dates, all_band_data, target_dates):
    """
    Perform linear interpolation for a single band across time
    with forward fill for beginning and backward fill for end
    """
    # Convert dates to numeric values (days since first date)
    date_nums = np.array([(d - all_dates[0]).days for d in all_dates])
    target_nums = np.array([(d - all_dates[0]).days for d in target_dates])

    # Get shape of the band
    band_shape = all_band_data[0].shape if all_band_data[0] is not None else None

    if band_shape is None:
        return None

    # Initialize array for interpolated data
    interpolated = np.full((len(target_dates), band_shape[0], band_shape[1]), np.nan)

    # Interpolate for each pixel
    for i in range(band_shape[0]):
        for j in range(band_shape[1]):
            # Extract time series for this pixel
            pixel_values = []
            pixel_dates = []

            for idx, band in enumerate(all_band_data):
                if band is not None and not np.isnan(band[i, j]):
                    pixel_values.append(band[i, j])
                    pixel_dates.append(date_nums[idx])

            if len(pixel_values) >= 2:
                # Sort by date
                sorted_indices = np.argsort(pixel_dates)
                pixel_dates_sorted = np.array(pixel_dates)[sorted_indices]
                pixel_values_sorted = np.array(pixel_values)[sorted_indices]

                # Create interpolation function
                interp_func = interp1d(pixel_dates_sorted, pixel_values_sorted,
                                       kind='linear', bounds_error=False, fill_value=np.nan)

                # Interpolate for all target dates
                interpolated_pixel = interp_func(target_nums)

                # Forward fill (ffill) for NaN values at the beginning
                # Find first non-NaN value and fill backwards
                first_valid_idx = np.where(~np.isnan(interpolated_pixel))[0]
                if len(first_valid_idx) > 0:
                    first_valid = first_valid_idx[0]
                    # Fill beginning with first valid value
                    interpolated_pixel[:first_valid] = interpolated_pixel[first_valid]

                # Backward fill (bfill) for NaN values at the end
                last_valid_idx = np.where(~np.isnan(interpolated_pixel))[0]
                if len(last_valid_idx) > 0:
                    last_valid = last_valid_idx[-1]
                    # Fill end with last valid value
                    interpolated_pixel[last_valid + 1:] = interpolated_pixel[last_valid]

                # Handle case where all values are NaN (no valid interpolation)
                if len(first_valid_idx) == 0:
                    interpolated_pixel[:] = np.nan

                interpolated[:, i, j] = interpolated_pixel

            elif len(pixel_values) == 1:
                # Only one valid observation - use it for all dates (constant fill)
                single_value = pixel_values[0]
                interpolated[:, i, j] = single_value

            else:
                # No valid observations - keep as NaN
                interpolated[:, i, j] = np.nan

    return interpolated


def process_landsat_interpolation(tif_files, start_date_str, end_date_str,
                                  cloud_band=23, band_mapping=None,
                                  output_dir="interpolated_output"):
    """
    Main function to process Landsat TIF files with cloud filtering and interpolation

    Parameters:
    -----------
    tif_files : list
        List of TIF file paths or filenames
    start_date_str : str
        Start date in 'YYYY-MM-DD' format
    end_date_str : str
        End date in 'YYYY-MM-DD' format
    cloud_band : int
        Band index for cloud cover (default: 23)
    band_mapping : dict
        Dictionary mapping band names to indices (default: DEFAULT_BAND_MAPPING)
    output_dir : str
        Directory to save output files (default: "interpolated_output")

    Returns:
    --------
    dict : Dictionary with interpolation results and metadata
    """

    # Use default band mapping if not provided
    if band_mapping is None:
        band_mapping = DEFAULT_BAND_MAPPING

    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Generate all dates between start and end
    target_dates = []
    current_date = start_date
    while current_date <= end_date:
        target_dates.append(current_date)
        current_date += timedelta(days=1)

    # Process each TIF file
    valid_files = []
    all_bands_data = {band_name: [] for band_name in band_mapping.keys()}
    all_dates = []

    for tif_file in tif_files:
        tif_path = Path(tif_file)
        if not tif_path.exists():
            continue

        # Parse date from filename
        file_date = parse_date_from_filename(tif_file)
        if file_date is None:
            continue


        # Filter clouds
        cloud_mask = filter_clouds(tif_path, cloud_band_index=cloud_band)

        # Extract required bands
        band_indices = list(band_mapping.values())
        bands_data = extract_bands(tif_path, band_indices)

        # Apply cloud mask
        masked_bands = apply_cloud_mask(bands_data, cloud_mask)

        # Store data for each band
        for idx, (band_name, band_idx) in enumerate(band_mapping.items()):
            if idx < len(masked_bands) and masked_bands[idx] is not None:
                all_bands_data[band_name].append(masked_bands[idx])
            else:
                all_bands_data[band_name].append(None)

        all_dates.append(file_date)
        valid_files.append(tif_file)


    # Perform linear interpolation for each band
    interpolated_results = {}

    for band_name, band_data_list in all_bands_data.items():
        # Remove None entries
        filtered_dates = []
        filtered_data = []

        for date, data in zip(all_dates, band_data_list):
            if data is not None:
                filtered_dates.append(date)
                filtered_data.append(data)

        if len(filtered_data) >= 2:
            interpolated = interpolate_band(filtered_dates, filtered_data, target_dates)
            interpolated_results[band_name] = interpolated
        else:
            interpolated_results[band_name] = None

    # Save interpolated results
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get reference metadata from first valid file
    with rasterio.open(valid_files[0]) as src:
        profile = src.profile
        profile.update({
            'count': len(band_mapping),
            'dtype': 'float32',
            'compress': 'lzw'
        })

    # Save each interpolated date
    saved_files = []

    for date_idx, target_date in enumerate(target_dates):
        # Collect bands for this date
        bands_for_date = []
        for band_name in band_mapping.keys():
            if interpolated_results[band_name] is not None:
                band_data = interpolated_results[band_name][date_idx]
                if band_data is not None:
                    bands_for_date.append(band_data)
                else:
                    bands_for_date.append(np.full((profile['height'], profile['width']), np.nan))
            else:
                bands_for_date.append(np.full((profile['height'], profile['width']), np.nan))

        # Create output filename
        output_filename = output_path / f"{target_date.strftime('%Y%m%d')}.tif"

        # Update profile for this output
        output_profile = profile.copy()
        output_profile['count'] = len(bands_for_date)

        # Write multi-band TIF
        with rasterio.open(output_filename, 'w', **output_profile) as dst:
            for band_idx, band_data in enumerate(bands_for_date, 1):
                dst.write(band_data.astype(np.float32), band_idx)

        saved_files.append(str(output_filename))


    # Create summary CSV
    summary_df = pd.DataFrame({
        'Date': [d.strftime('%Y-%m-%d') for d in target_dates],
        'Output_File': [f"{d.strftime('%Y%m%d')}.tif" for d in target_dates]
    })


    # Return results metadata
    return {
        'output_directory': str(output_path),
        'target_dates': target_dates,
        'saved_files': saved_files,
        'bands_processed': list(band_mapping.keys())
    }
