import os
import glob
import time
import numpy as np
import rasterio as rio
import spyndex


def safe_replace(src_path, dst_path, max_retries=3, delay=0.5):
    """Safely replace a file with retry mechanism"""
    for attempt in range(max_retries):
        try:
            # Try to remove the destination if it exists
            if os.path.exists(dst_path):
                os.remove(dst_path)
            # Rename the temp file
            os.rename(src_path, dst_path)
            return True
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                continue
            else:
                raise e
    return False


def add_vis_to_existing_files(directory, file_pattern="*.tif"):
    """
    Add calculated bands as additional bands to existing files.
    Original bands remain unchanged, new bands are appended.
    """

    full_pattern = os.path.join(directory, file_pattern)
    tiff_files = sorted(glob.glob(full_pattern))

    if not tiff_files:
        raise ValueError(f"No TIFF files found in {directory}")

    for tiff_file in tiff_files:
        # Read original file
        with rio.open(tiff_file) as src:
            original_bands = src.read()
            original_count = src.count
            profile = src.profile.copy()

            # Check if we have enough bands
            if original_count < 12:
                print(f"  ⚠ Warning: File has only {original_count} bands, expected at least 12")
                continue

            # Read specific bands for calculations
            SR_B2 = original_bands[1]  # Band 2 (Blue)
            SR_B3 = original_bands[2]  # Band 3 (Green)
            SR_B4 = original_bands[3]  # Band 4 (Red)
            SR_B5 = original_bands[4]  # Band 5 (NIR)
            SR_B6 = original_bands[5]  # Band 6 (SWIR1)
            SR_B7 = original_bands[6]  # Band 7 (SWIR2)

            # LE bands (bands 9-12 in 1-indexed, indices 8-11 in 0-indexed)
            LE = original_bands[8]  # Band 9
            LEc = original_bands[9]  # Band 10
            LEs = original_bands[10]  # Band 11
            ETrF = original_bands[11]  # Band 12

            # Calculate new bands
            new_bands = []
            new_band_names = []
            old_band_names = ['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'ST_B10', 'LE', 'LEc', 'LEs', 'ETrF']

            # Calculate LE ratios
            valid_mask = (LE != 0) & (~np.isnan(LE))

            LEc_ratio = np.full_like(LE, np.nan, dtype=np.float32)
            LEs_ratio = np.full_like(LE, np.nan, dtype=np.float32)

            if np.any(valid_mask):
                LEc_ratio[valid_mask] = LEc[valid_mask] / LE[valid_mask]
                LEs_ratio[valid_mask] = LEs[valid_mask] / LE[valid_mask]

            new_bands.append(LEc_ratio)
            new_band_names.append('LEc_ratio')

            new_bands.append(LEs_ratio)
            new_band_names.append('LEs_ratio')


            # Calculate spectral indices
            params = {
                "B": SR_B2.astype(np.float32),
                "G": SR_B3.astype(np.float32),
                "R": SR_B4.astype(np.float32),
                "N": SR_B5.astype(np.float32),
                "S1": SR_B6.astype(np.float32),
                "S2": SR_B7.astype(np.float32),
                'L': 1,
                'gamma': 1,
                'sla': 1,
                'slb': 0,
                'alpha': 0.1,
                'epsilon': 1,
                'g': 2.5,
                'C1': 6.0,
                'C2': 7.5,
                'nexp': 1,
                'omega': 0.5,
                'k': 1,
                'cexp': 1,
                'fdelta': 0.5,
            }

            # Compute each index
            indices_to_compute = ['IAVI', 'GLI', 'ExGR', 'SEVI']
            for idx_name in indices_to_compute:
                try:
                    result = spyndex.computeIndex(index=idx_name, params=params)
                    if isinstance(result, np.ndarray):
                        new_bands.append(result.astype(np.float32))
                        new_band_names.append(idx_name)
                    else:
                        print(f"  ✗ {idx_name} returned unexpected format: {type(result)}")
                except Exception as e:
                    print(f"  ✗ Failed to compute {idx_name}: {e}")
                    nan_band = np.full(SR_B2.shape, np.nan, dtype=np.float32)
                    new_bands.append(nan_band)
                    new_band_names.append(f'{idx_name}_failed')

            # Combine original and new bands
            all_bands = [original_bands[i] for i in range(original_count)]
            all_bands.extend(new_bands)

            # Update profile for new band count
            profile.update({
                'count': len(all_bands),
                'dtype': np.float32
            })

            # Write to temp file in a different directory to avoid conflicts
            temp_dir = os.path.join(directory, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, os.path.basename(tiff_file) + '.temp')

            with rio.open(temp_path, 'w', **profile) as dst:
                for i, band in enumerate(all_bands, 1):
                    if band.ndim == 3:
                        band = band[0]

                    if band.dtype != np.float32:
                        band = band.astype(np.float32)

                    dst.write(band, i)

                    if i <= original_count:
                        dst.set_band_description(i, old_band_names[i-1])
                    else:
                        idx = i - original_count - 1
                        dst.set_band_description(i, new_band_names[idx])

        # Close the original file explicitly and wait a moment
        time.sleep(0.001)

        # Replace original with temp file
        try:
            safe_replace(temp_path, tiff_file)
        except Exception as e:
            print(f"  ✗ Failed to replace file: {e}")
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        # Clean up temp directory if empty
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass  # Directory not empty, that's fine