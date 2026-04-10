import os
import numpy as np
import xarray as xr
import rioxarray
import pyet


def add_et0_bands_to_raster_rio(tif_file, overwrite=False):
    """
    Calculate ET0 and ETrF and add them as new bands using rioxarray.

    Parameters:
    -----------
    tif_file : str
        Path to the input raster file
    overwrite : bool
        If True, overwrite the original file with new bands added.
        If False, create a new file with '_with_ET0' suffix.

    Returns:
    --------
    str
        Path to the output file
    """

    # Validate input file exists
    if not os.path.exists(tif_file):
        raise FileNotFoundError(f"File not found: {tif_file}")

    # Open the raster with rioxarray
    ds = rioxarray.open_rasterio(tif_file, masked=True)

    # Extract required bands (assuming band dimension is 'band')
    # rioxarray typically uses band dimension
    band34 = ds.sel(band=34)  # Wind speed
    band47 = ds.sel(band=47)  # Net radiation
    band46 = ds.sel(band=46)  # Soil heat flux
    band26 = ds.sel(band=26)  # Temperature (Kelvin)
    band25 = ds.sel(band=25)  # Pressure
    band40 = ds.sel(band=40)  # Relative humidity
    band41 = ds.sel(band=41)  # Actual ET

    # Calculate derived variables
    wind_speed_2m = band34 * (4.87 / (np.log(67.8 * 10 - 5.42)))
    Rn_MJ = band47 * 0.0036
    G_MJ = band46 * 0.0036
    Ta_C = band26 - 273.15
    P_kPa = band25 * 0.001
    relative_humidity = band40

    # Calculate ET0 (Reference Evapotranspiration)
    # pyet.pm_asce works with xarray DataArrays!

    ETr_inst = pyet.pm_asce(tmean=Ta_C,
                            wind=wind_speed_2m,
                            rn=Rn_MJ,
                            g=G_MJ,
                            rh=relative_humidity,
                            pressure=P_kPa,
                            cn=37,
                            cd=0.23)

    lamb = 2.501 - 0.002361 * Ta_C
    ET_inst = band41 * 3600 / (lamb * 1000000)

    ETrF =  ET_inst/ ETr_inst
    # Handle division by zero
    ETrF = ETrF.where(ETr_inst != 0, np.nan)
    ETrF = ETrF.clip(0,1)


    # Create new dataset with original bands plus new ones
    # First, get all original bands
    bands_list = []
    for band_num in range(1, ds.sizes['band'] + 1):
        bands_list.append(ds.sel(band=band_num))

    # Add new bands
    bands_list.append(ETr_inst.expand_dims(band={'band': [ds.sizes['band'] + 1]}))
    bands_list.append(ETrF.expand_dims(band={'band': [ds.sizes['band'] + 2]}))

    # Concatenate along band dimension
    new_ds = xr.concat(bands_list, dim='band')

    # Copy attributes from original
    new_ds.attrs = ds.attrs
    new_ds.rio.write_crs(ds.rio.crs, inplace=True)
    new_ds.rio.write_transform(ds.rio.transform(), inplace=True)

    # Determine output file path
    if overwrite:
        output_file = tif_file
    else:
        output_file = tif_file.replace('.tif', '_with_ET0.tif')

    new_ds = new_ds.transpose('band', 'y', 'x')
    new_ds.rio.to_raster(output_file, dtype='float32', compress='lzw')

    return output_file


def process_et0_all_rasters_rio(input_directory, overwrite=True, file_pattern='.tif'):
    """
    Process all raster files in a directory to add ET0 bands using rioxarray.

    Parameters:
    -----------
    input_directory : str
        Directory containing the raster files
    overwrite : bool
        If True, overwrite original files. If False, create new files with suffix.
    file_pattern : str
        File extension pattern to match (default: '.tif')

    Returns:
    --------
    list
        List of output file paths
    """

    # Get all raster files
    img_lst = [os.path.join(input_directory, i)
               for i in os.listdir(input_directory)
               if i.endswith(file_pattern)]

    if not img_lst:
        print(f"No {file_pattern} files found in {input_directory}")
        return []

    output_files = []

    for tif_file in img_lst:
        try:
            output_file = add_et0_bands_to_raster_rio(tif_file, overwrite=overwrite)
            output_files.append(output_file)
        except Exception as e:
            print(f"Error processing {tif_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    return output_files


# Alternative approach: Process as a single function with explicit array handling
def calculate_et0_from_arrays(band34, band47, band46, band26, band25, band40):
    """
    Calculate ET0 from numpy arrays or xarray DataArrays.
    This helper function can be used if pyet.pm_asce is having issues with xarray.

    Parameters:
    -----------
    band34, band47, band46, band26, band25, band40 : array-like
        Input bands as numpy arrays or xarray DataArrays

    Returns:
    --------
    ETr_inst : array-like
        Reference evapotranspiration
    """

    # Convert to numpy if they're xarray
    import xarray as xr
    if isinstance(band34, xr.DataArray):
        # Keep coordinates but extract data for calculation
        coords = band34.coords
        dims = band34.dims

        wind_speed_2m = band34.values * (4.87 / (np.log(67.8 * 10 - 5.42)))
        Rn_MJ = band47.values * 0.0036
        G_MJ = band46.values * 0.0036
        Ta_C = band26.values - 273.15
        P_kPa = band25.values * 0.001
        rh = band40.values

        # Calculate ET0
        ETr_inst_values = pyet.pm_asce(tmean=Ta_C,
                                       wind=wind_speed_2m,
                                       rn=Rn_MJ,
                                       g=G_MJ,
                                       rh=rh,
                                       pressure=P_kPa,
                                       cn=37,
                                       cd=0.23)

        # Recreate xarray DataArray
        ETr_inst = xr.DataArray(ETr_inst_values,
                                coords=coords,
                                dims=dims,
                                attrs={'units': 'mm/day',
                                       'long_name': 'Reference ET'})
    else:
        # Handle numpy arrays
        wind_speed_2m = band34 * (4.87 / (np.log(67.8 * 10 - 5.42)))
        Rn_MJ = band47 * 0.0036
        G_MJ = band46 * 0.0036
        Ta_C = band26 - 273.15
        P_kPa = band25 * 0.001
        rh = band40

        ETr_inst = pyet.pm_asce(tmean=Ta_C,
                                wind=wind_speed_2m,
                                rn=Rn_MJ,
                                g=G_MJ,
                                rh=rh,
                                pressure=P_kPa,
                                cn=37,
                                cd=0.23)

    return ETr_inst


# Example usage with proper error handling for pyet
def add_et0_bands_safe(tif_file, overwrite=False):
    """
    Safe version with explicit type conversion for pyet compatibility.
    """
    import xarray as xr
    import rioxarray

    ds = rioxarray.open_rasterio(tif_file, masked=True)

    # Extract bands and ensure they're numpy arrays for pyet
    band34 = ds.sel(band=34).values
    band47 = ds.sel(band=47).values
    band46 = ds.sel(band=46).values
    band26 = ds.sel(band=26).values
    band25 = ds.sel(band=25).values
    band40 = ds.sel(band=40).values
    band41 = ds.sel(band=41).values

    # Get coordinates for later
    coords = ds.sel(band=34).coords
    dims = ds.sel(band=34).dims

    # Calculate derived variables
    wind_speed_2m = band34 * (4.87 / (np.log(67.8 * 10 - 5.42)))
    Rn_MJ = band47 * 0.0036
    G_MJ = band46 * 0.0036
    Ta_C = band26 - 273.15
    P_kPa = band25 * 0.001
    rh = band40

    # Handle NaN values
    mask = ~(np.isnan(band34) | np.isnan(band47) | np.isnan(band46) |
             np.isnan(band26) | np.isnan(band25) | np.isnan(band40))

    # Calculate ET0 only for valid pixels
    ETr_inst = np.full_like(band34, np.nan, dtype=np.float32)

    if np.any(mask):
        ETr_inst_valid = pyet.pm_asce(tmean=Ta_C[mask],
                                      wind=wind_speed_2m[mask],
                                      rn=Rn_MJ[mask],
                                      g=G_MJ[mask],
                                      rh=rh[mask],
                                      pressure=P_kPa[mask],
                                      cn=37,
                                      cd=0.23)
        ETr_inst[mask] = ETr_inst_valid

    # Calculate ETrF
    ETrF = np.full_like(band34, np.nan, dtype=np.float32)
    valid_et_mask = mask & (ETr_inst != 0)
    if np.any(valid_et_mask):
        ETrF[valid_et_mask] = band41[valid_et_mask] / ETr_inst[valid_et_mask]

    # Convert back to DataArrays
    ETr_inst_da = xr.DataArray(ETr_inst, coords=coords, dims=dims)
    ETrF_da = xr.DataArray(ETrF, coords=coords, dims=dims)

    # Add attributes
    ETr_inst_da.attrs = {'long_name': 'Reference ET', 'units': 'mm/day'}
    ETrF_da.attrs = {'long_name': 'ET Fraction', 'units': 'fraction'}

    # Combine datasets
    new_ds = xr.concat([ds, ETr_inst_da.expand_dims('band'),
                        ETrF_da.expand_dims('band')], dim='band')

    # Update band numbers
    new_ds = new_ds.assign_coords(band=list(range(1, new_ds.sizes['band'] + 1)))

    # Save
    output_file = tif_file if overwrite else tif_file.replace('.tif', '_with_ET0.tif')
    new_ds.rio.to_raster(output_file, dtype='float32', compress='lzw')

    return output_file