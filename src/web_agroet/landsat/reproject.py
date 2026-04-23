import rasterio
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.transform import from_origin
import os
import numpy as np


def reproject_landsat_to_wgs84(input_path, target_resolution=0.0003):
    """
    Reproject Landsat image to EPSG:4326 (WGS84) using a fixed reference grid.
    Ensures same pixels for same geographic area.

    Args:
        input_path (str): Path to the input Landsat image file
        target_resolution (float): Target pixel resolution in degrees (default 0.0003 ~ 30m at equator)

    Returns:
        str: Path to the reprojected file, or None if error
    """

    # Extract date from filename
    filename = os.path.basename(input_path)
    try:
        img_part = filename.split('LC0')[1]
        date = img_part.split('_')[2]
    except:
        date = filename.split('.')[0]

    # Create output filename in same directory
    directory = os.path.dirname(input_path)
    if directory:
        output_path = os.path.join(directory, f"{date}.tif")
    else:
        output_path = f"{date}.tif"

    try:
        with rasterio.open(input_path) as src:
            # Get the bounds in target CRS (WGS84)
            left, bottom, right, top = transform_bounds(
                src.crs, 'EPSG:4326', *src.bounds
            )

            # Round bounds to create a consistent grid
            # This ensures alignment across different files
            left = np.floor(left / target_resolution) * target_resolution
            right = np.ceil(right / target_resolution) * target_resolution
            top = np.ceil(top / target_resolution) * target_resolution
            bottom = np.floor(bottom / target_resolution) * target_resolution

            # Calculate output dimensions
            width = int(round((right - left) / target_resolution))
            height = int(round((top - bottom) / target_resolution))

            # Create transform for fixed grid (upper-left origin)
            transform = from_origin(left, top, target_resolution, target_resolution)

            # Update metadata
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': 'EPSG:4326',
                'transform': transform,
                'width': width,
                'height': height,
                'driver': 'GTiff'
            })

            # Create output file
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for band_idx in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band_idx),
                        destination=rasterio.band(dst, band_idx),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs='EPSG:4326',
                        resampling=Resampling.bilinear
                    )

        # Delete original file
        os.remove(input_path)
        return output_path

    except Exception as e:
        print(f"✗ Error during reprojection: {str(e)}")
        return None

def reproject_landsat_to_wgs842(input_path):
    """
    Reproject Landsat image to EPSG:4326 (WGS84) and save with date from filename.
    Deletes the original file after successful reprojection.
    Uses only rasterio, no GDAL dependency.

    Args:
        input_path (str): Path to the input Landsat image file

    Returns:
        str: Path to the reprojected file, or None if error
    """

    # Extract date from filename
    filename = os.path.basename(input_path)
    img_part = filename.split('LC0')[1]
    date = img_part.split('_')[2]

    # Create output filename in same directory
    directory = os.path.dirname(input_path)
    if directory:
        output_path = os.path.join(directory, f"{date}.tif")
    else:
        output_path = f"{date}.tif"

    try:
        # Open source file
        with rasterio.open(input_path) as src:
            # Calculate transform and dimensions for new CRS
            transform, width, height = calculate_default_transform(
                src.crs,  # Source CRS
                'EPSG:4326',  # Target CRS
                src.width,  # Source width
                src.height,  # Source height
                *src.bounds  # Source bounds (left, bottom, right, top)
            )

            # Update metadata for the new file
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': 'EPSG:4326',
                'transform': transform,
                'width': width,
                'height': height
            })

            # Create output file and reproject band by band
            with rasterio.open(output_path, 'w', **kwargs) as dst:
                for band_idx in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band_idx),
                        destination=rasterio.band(dst, band_idx),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs='EPSG:4326',
                        resampling=Resampling.bilinear
                    )

        # IMPORTANT: Source file is now closed (exited the 'with' block)
        # Now we can safely delete the original file
        os.remove(input_path)

        return output_path

    except rasterio.errors.CRSError as e:
        return None
    except PermissionError as e:
        print(f"✗ Permission Error: {str(e)}")
        print("  Make sure no other program is using the file")
        return None
    except Exception as e:
        print(f"✗ Error during reprojection: {str(e)}")
        return None
