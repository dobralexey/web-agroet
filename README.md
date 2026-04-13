# 🌾 AgroET - Web Interface for Evapotranspiration Modeling

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://agroet.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**AgroET** is a web-based application for estimating spatial and temporal distribution of evapotranspiration (ET), transpiration (ETc), and soil evaporation (ETs) over agricultural fields using satellite remote sensing data, meteorological reanalysis, and machine learning techniques.

## 📖 Overview

This application implements the **ML PT-JPL model** — an enhanced version of the Priestley-Taylor Jet Propulsion Laboratory (PT-JPL) evapotranspiration model corrected using gradient boosting machine learning (CatBoost). The model was developed and validated using eddy covariance flux tower measurements from 137 stations worldwide.

### Key Features

- **Dual Area Selection**: Upload shapefiles (ZIP, GeoJSON, GeoPackage) or draw polygons directly on an interactive map
- **Two Modeling Approaches**:
  - **ML PT-JPL**: Machine learning-corrected energy balance model (recommended)
  - **Original PT-JPL**: Classic physical model
- **Multi-band Output**: 21 output bands including ET, ETc, ETs, vegetation indices, and intermediate variables
- **Interactive Visualization**:
  - Time series plots with Savitzky-Golay smoothing
  - Spatial distribution maps with Google Hybrid/Satellite basemaps
  - Histograms and statistical summaries
- **Data Export**: Download all results as GeoTIFF, CSV timeseries, or meteorological data (Feather format)
- **Bilingual Interface**: Full support for English and Russian languages

## 🚀 Live Demo

Try the application online: **[https://agroet.streamlit.app/](https://agroet.streamlit.app/)**

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- Google Earth Engine account (for Landsat data access)

### Local Setup

1. **Clone the repository:**
```bash
git clone https://github.com/dobralexey/web-agroet.git
cd web-agroet
