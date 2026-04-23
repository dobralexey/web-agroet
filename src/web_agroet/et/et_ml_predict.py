import numpy as np
import pandas as pd
import xarray as xr
import rioxarray as rxr
from catboost import CatBoostRegressor
import glob
from pathlib import Path
from datetime import datetime
import warnings


warnings.filterwarnings('ignore')

BAND_NAMES = [
    'SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7',
    'ST_B10', 'LE', 'LEc', 'LEs', 'ETrF', 'LEc_ratio', 'LEs_ratio',
    'IAVI', 'GLI', 'ExGR', 'SEVI', 'ET', 'ETc', 'ETs'
]

class ETPredictor:
    def __init__(self, images_dir, ml_model_path, df_meteo, use_original_ptjpl=False):
        """
        Initialize ET predictor

        Parameters:
        -----------
        images_dir : str
            Path to directory with daily satellite images
        ml_model_path : str
            Path to CatBoost model file (only used if use_original_ptjpl=False)
        df_meteo : pd.DataFrame
            Daily meteorological data with date as index
        use_original_ptjpl : bool
            If True, use original method from METRIC (ET = ETr_24_ERA * ETrF)
            If False, use ML model
        """
        self.images_dir = Path(images_dir)
        self.use_original_ptjpl = use_original_ptjpl
        self.df_meteo = df_meteo

        # Ensure Date column is datetime
        if 'Date' in self.df_meteo.columns:
            self.df_meteo['Date'] = pd.to_datetime(self.df_meteo['Date'])
        elif self.df_meteo.index.name == 'Date' or isinstance(self.df_meteo.index, pd.DatetimeIndex):
            self.df_meteo = self.df_meteo.reset_index()
            self.df_meteo.rename(columns={'index': 'Date'}, inplace=True)

        if not use_original_ptjpl:
            # Load ML model only if using ML approach
            self.model = CatBoostRegressor()
            self.model.load_model(ml_model_path)
            self.feature_names = self.model.feature_names_
        else:
            self.model = None
            self.feature_names = None

    def load_satellite_image(self, date_str):
        """Load satellite image for a specific date"""
        tif_file = self.images_dir / f"{date_str}.tif"
        if not tif_file.exists():
            raise FileNotFoundError(f"Image not found: {tif_file}")

        # Load using rioxarray
        img = rxr.open_rasterio(tif_file)
        return img

    def extract_pixel_features(self, img):
        """
        Extract features from satellite image for each pixel

        For original method, only needs ETrF from band 12
        """
        if len(img.shape) == 3:  # (band, y, x)
            n_bands, height, width = img.shape

            features = {}

            if self.use_original_ptjpl:
                # Original method only needs ETrF from band 12
                # Band index 12 (0-indexed) corresponds to band 13 in 1-indexed
                if n_bands < 13:
                    raise ValueError(f"Image has only {n_bands} bands but need at least 13 bands for ETrF")
                features['LEc_ratio'] = img[12].values.flatten()  # band 13
                features['LEs_ratio'] = img[13].values.flatten()  # band 14
                features['ETrF'] = img[11].values.flatten()  # band 12 (0-indexed = 12)
            else:
                # ML method needs all features
                if n_bands < 17:
                    raise ValueError(f"Image has only {n_bands} bands but need at least 17 bands for indices 12-16")

                features['IAVI'] = img[14].values.flatten()  # band 15 (0-indexed)
                features['GLI'] = img[15].values.flatten()
                features['ExGR'] = img[16].values.flatten()
                features['SEVI'] = img[17].values.flatten()
                features['LEc_ratio'] = img[12].values.flatten()  # band 13
                features['LEs_ratio'] = img[13].values.flatten()  # band 14

            return features, height, width

        else:
            raise ValueError(f"Unexpected image shape: {img.shape}")

    def prepare_features_for_prediction(self, features_dict, meteo_data):
        if self.use_original_ptjpl:
            raise NotImplementedError("prepare_features_for_prediction is only for ML method")

        n_pixels = len(list(features_dict.values())[0])

        # Create feature matrix
        feature_matrix = []
        feature_names_used = []  # Track feature names for DataFrame columns

        # Add satellite features
        for feature_name in self.feature_names:
            if feature_name in features_dict:
                feature_matrix.append(features_dict[feature_name])
                feature_names_used.append(feature_name)
            elif feature_name in meteo_data.index:
                # Repeat meteo data for all pixels
                feature_matrix.append(np.full(n_pixels, meteo_data[feature_name]))
                feature_names_used.append(feature_name)
            else:
                raise ValueError(f"Feature {feature_name} not found in satellite or meteo data")

        # Convert to DataFrame
        feature_array = np.column_stack(feature_matrix)
        return pd.DataFrame(feature_array, columns=feature_names_used)

    def prepare_features_for_prediction2(self, features_dict, meteo_data):
        """
        Combine satellite features with meteorological data for model input

        Only used for ML method
        """
        if self.use_original_ptjpl:
            raise NotImplementedError("prepare_features_for_prediction is only for ML method")

        n_pixels = len(list(features_dict.values())[0])

        # Create feature matrix
        feature_matrix = []

        # Add satellite features
        for feature_name in self.feature_names:
            if feature_name in features_dict:
                feature_matrix.append(features_dict[feature_name])
            elif feature_name in meteo_data.index:
                # Repeat meteo data for all pixels
                feature_matrix.append(np.full(n_pixels, meteo_data[feature_name]))
            else:
                raise ValueError(f"Feature {feature_name} not found in satellite or meteo data")
        return np.column_stack(feature_matrix)

    def predict_et_for_image(self, date_str, return_as_raster=True):
        """
        Predict ET for all pixels in an image

        Parameters:
        -----------
        date_str : str
            Date string in YYYYMMDD format
        return_as_raster : bool
            If True, return xarray DataArray, else return numpy array

        Returns:
        --------
        Dictionary with ET, ETc, ETs predictions and enhanced image
        """
        # Load image
        img = self.load_satellite_image(date_str)

        # Extract pixel features
        features_dict, height, width = self.extract_pixel_features(img)

        # Get meteorological data for this date
        date_obj = pd.to_datetime(date_str)
        meteo_row = self.df_meteo[self.df_meteo['Date'] == date_obj]

        if len(meteo_row) == 0:
            raise ValueError(f"No meteorological data found for date {date_str}")

        meteo_data = meteo_row.iloc[0]

        if self.use_original_ptjpl:
            # Alternative method: ET = ETr_24_ERA * ETrF
            # Get ETr_24_ERA from meteorological data
            if 'ETr_24_ERA' not in meteo_data.index:
                raise ValueError("ETr_24_ERA not found in meteorological data")

            etr_24_era = meteo_data['ETr_24_ERA']
            etrf_map = features_dict['ETrF'].reshape(height, width)

            # Calculate ET (total evapotranspiration)
            et_map = etr_24_era * etrf_map

            # For alternative method, we don't have LEc_ratio and LEs_ratio
            # So we cannot separate into ETc and ETs
            # We'll set them to NaN or estimate based on defaults
            etc_map = et_map * features_dict['LEc_ratio'].reshape(height, width)
            ets_map = et_map * features_dict['LEs_ratio'].reshape(height, width)

        else:
            # ML method
            X = self.prepare_features_for_prediction(features_dict, meteo_data)
            et_predictions = self.model.predict(X)
            et_map = et_predictions.reshape(height, width)

            # Calculate ETc and ETs from ratios
            etc_map = et_map * features_dict['LEc_ratio'].reshape(height, width)
            ets_map = et_map * features_dict['LEs_ratio'].reshape(height, width)

        # Create enhanced image with original bands + ET bands

        original_bands = img.values

        # Add new bands (ET, ETc, ETs)
        new_bands = np.stack([
            et_map,
            etc_map,
            ets_map
        ], axis=0)

        # Combine original bands with new ET bands
        enhanced_img = np.concatenate([original_bands, new_bands], axis=0)

        # Update band names
        n_original_bands = original_bands.shape[0]
        band_names = [f'band_{i + 1}' for i in range(n_original_bands)]
        band_names.extend(['ET', 'ETc', 'ETs'])

        # Create xarray DataArray with enhanced image
        enhanced_da = xr.DataArray(
            enhanced_img,
            dims=('band', 'y', 'x'),
            coords={
                'band': band_names,
                'y': img.y,
                'x': img.x
            },
        )

        # Copy CRS information
        enhanced_da.rio.write_crs(img.rio.crs, inplace=True)

        results = {
            'et': et_map,
            'etc': etc_map,
            'ets': ets_map,
            'enhanced_image': enhanced_da,
            'method_used': 'original' if self.use_original_ptjpl else 'ml'
        }
        return results

    def process_all_images(self, date_range=None, output_dir='./et_predictions',
                           save_enhanced=True):
        """
        Process multiple images and save predictions

        Parameters:
        -----------
        date_range : list or None
            List of date strings to process. If None, process all available images
        output_dir : str
            Directory to save ET predictions
        save_enhanced : bool
            Save enhanced images with ET bands included
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)

        enhanced_dir = output_dir
        enhanced_dir.mkdir(exist_ok=True)

        # Get all tif files
        if date_range is None:
            tif_files = sorted(self.images_dir.glob('*.tif'))
            date_strings = [f.stem for f in tif_files]
        else:
            date_strings = date_range

        results = {}
        method_name = 'original ptjpl' if self.use_original_ptjpl else 'ml'

        for date_str in date_strings:
            try:
                prediction_results = self.predict_et_for_image(date_str)

                if save_enhanced:
                    # Save enhanced image (original + ET bands)
                    enhanced_file = enhanced_dir / f"{date_str}.tif"
                    prediction_results['enhanced_image'].rio.to_raster(enhanced_file, band_names=BAND_NAMES)


                # Store results without the enhanced image (to save memory)
                results[date_str] = {
                    'et': prediction_results['et'],
                    'etc': prediction_results['etc'],
                    'ets': prediction_results['ets'],
                    'method': method_name
                }

            except Exception as e:
                print(f"Error processing {date_str}: {str(e)}")
                continue

        return results

    def compare_methods(self, date_str):
        """
        Compare ML and alternative methods for the same date

        Parameters:
        -----------
        date_str : str
            Date string in YYYYMMDD format

        Returns:
        --------
        Dictionary with results from both methods
        """
        # Run ML method
        self.use_original_ptjpl = False
        ml_results = self.predict_et_for_image(date_str)

        # Run alternative method
        self.use_original_ptjpl = True
        alt_results = self.predict_et_for_image(date_str)

        # Restore original setting
        self.use_original_ptjpl = False

        # Calculate statistics
        comparison = {
            'date': date_str,
            'ml': {
                'et_mean': np.nanmean(ml_results['et']),
                'et_std': np.nanstd(ml_results['et']),
                'et_min': np.nanmin(ml_results['et']),
                'et_max': np.nanmax(ml_results['et'])
            },
            'original': {
                'et_mean': np.nanmean(alt_results['et']),
                'et_std': np.nanstd(alt_results['et']),
                'et_min': np.nanmin(alt_results['et']),
                'et_max': np.nanmax(alt_results['et'])
            },
            'difference': {
                'mean_diff': np.nanmean(ml_results['et'] - alt_results['et']),
                'rmse': np.sqrt(np.nanmean((ml_results['et'] - alt_results['et']) ** 2)),
                'mae': np.nanmean(np.abs(ml_results['et'] - alt_results['et']))
            }
        }

        return comparison

