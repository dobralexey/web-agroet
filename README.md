# ML PT-JPL Model Web Interface

> 🌍 [English](#english) | [Русский](#russian)

---

<a name="english"></a>
## 🇬🇧 English

### Overview

The **ML PT-JPL Model Web Interface** is a Streamlit-based application for estimating actual evapotranspiration (ET) over agricultural fields using Landsat satellite imagery and ERA5-Land meteorological reanalysis data. It supports two model variants:

- **ML PT-JPL** — a machine-learning model that use the Priestley–Taylor Jet Propulsion Laboratory model to separate ET into transpiration (ETc) and soil evaporation (ETc)
- **Original PT-JPL** — the classic physically-based PT-JPL model

The app retrieves satellite data via Google Earth Engine (GEE) and outputs multi-band GeoTIFF files alongside meteorological time-series data.
Web-interface is hosted in https://agroet.stremalit.app

---

### ⚠️ Important Limitations

> **One field per run.** Each run is designed for a **single agricultural field**. Submitting a shapefile with multiple polygons or a very large area may produce unreliable results.

> **One year per run (recommended).** The application has been tested for date ranges of **up to one year**. Longer periods have not been validated and may cause errors or very long processing times.

> **Need more fields or years?** Simply run the model multiple times — once per field and/or year — and download the results after each run. All outputs are independent and can be combined manually.

---

### Features

- **Two area input methods:** upload a shapefile (`.zip`, `.geojson`, `.gpkg`) or draw a polygon interactively on the map
- **Flexible date range selection** from 2013 onward (Landsat 8/9 era)
- **Cloud cover filter** to exclude cloudy Landsat scenes
- **Interactive map viewer** to explore results band by band and date by date
- **Time-series plot** of ET, ETc (transpiration), ETs (soil evaporation), and ETr (reference ETr calculated from ERA5-Land)
- **Downloadable outputs:**
  - Multi-band GeoTIFF files (one per Landsat acquisition date)
  - ERA5-Land meteorological data (`.feather`)
  - Combined time-series CSV
- **Bilingual interface** (English / Russian)

---

### How to Use

1. **Select your area input method** in the left panel — upload a shapefile or draw a polygon on the map.
   - Use **one agricultural field only** (a single polygon).
2. **Set the date range** — start date and end date. A range of up to one year is recommended and tested.
3. **Choose the model** — ML PT-JPL or Original PT-JPL.
4. **Set the maximum cloud cover** percentage (lower values give cleaner imagery but fewer available scenes).
5. **Click "🚀 Run PT-JPL Model"** and wait for processing to complete.
6. **Download your results** using the buttons that appear after processing:
   - TIFF files (zipped)
   - Meteorological data
   - Combined time-series CSV
7. **Explore the map viewer** on the right to inspect individual bands and dates.

To analyse **another field or another year**, simply repeat the steps above with the new inputs. Each run is independent.

---

### Output Bands (GeoTIFF)

| Band | Description |
|------|-------------|
| 1–7 | Landsat surface reflectance (B1–B7) |
| 8 | Thermal band (ST_B10) |
| 9 | Latent Heat Flux LE (W/m²) |
| 10 | Canopy LE — LEc (W/m²) |
| 11 | Soil LE — LEs (W/m²) |
| 12 | Evapotranspiration Fraction — ETrF |
| 13–14 | LEc ratio, LEs ratio |
| 15–18 | Vegetation indices (IAVI, GLI, ExGR, SEVI) |
| 19 | ET — actual evapotranspiration (mm/day) |
| 20 | ETc — transpiration (mm/day) |
| 21 | ETs — soil evaporation (mm/day) |

---

### Requirements

- Python 3.9+
- Google Earth Engine account with a valid service account configured in Streamlit secrets
- Dependencies: `streamlit`, `earthengine-api`, `geopandas`, `rasterio`, `folium`, `streamlit-folium`, `scipy`, `pandas`, `matplotlib`, `Pillow`, `branca`

---

### Secrets Configuration (Streamlit Cloud)

Add your GEE service account credentials to `.streamlit/secrets.toml` if you use app locally:

```toml
[gee_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "..."
```

---

---

<a name="russian"></a>
## 🇷🇺 Русский

### Обзор

**Веб-интерфейс модели ML PT-JPL** — приложение на основе Streamlit для оценки актуальной эвапотранспирации (ET) сельскохозяйственных полей по данным спутников Landsat и климатического реанализа ERA5-Land. Поддерживаются две версии модели:

- **ML PT-JPL** — модель машинного обучения, которая использует модель PT-JPL для разделения эвапотранспирации (ET) на транспирацию (ETc) и испарение с поверхности почвы (ETs)
- **Original PT-JPL** — классическая энергобалансовая модель PT-JPL

Спутниковые данные загружаются через Google Earth Engine (GEE). Результаты — многоканальные GeoTIFF-файлы и метеорологические временные ряды.
Веб-интерфейс расположен по адресу: https://agroet.stremalit.app

---

### ⚠️ Важные ограничения

> **Одно поле за один запуск.** Приложение рассчитано на **одно сельскохозяйственное поле**. Загрузка shapefile с несколькими полигонами или очень большой территорией может привести к некорректным результатам.

> **Один год за один запуск (рекомендуется).** Приложение тестировалось на периодах **не более одного года**. Более длинные периоды не проверялись и могут вызвать ошибки или очень долгое время обработки.

> **Нужно больше полей или лет?** Просто запустите модель несколько раз — по одному запуску на поле и/или год — и скачивайте результаты после каждого запуска. Все результаты независимы и могут быть объединены вручную.

---

### Возможности

- **Два способа задания области:** загрузка shapefile (`.zip`, `.geojson`, `.gpkg`) или рисование полигона на интерактивной карте
- **Гибкий выбор дат** начиная с 2013 года (эпоха Landsat 8/9)
- **Фильтр облачности** для исключения облачных снимков Landsat
- **Интерактивный просмотр карт** по каналам и датам
- **График временного ряда** ET, ETc (транспирация), ETs (испарение с поверхности почвы) и ETr (эталонная ETr по ERA5-Land)
- **Загрузка результатов:**
  - Многоканальные GeoTIFF-файлы (один на дату съёмки Landsat)
  - Метеорологические данные ERA5-Land (`.feather`)
  - Объединённый временной ряд в формате CSV
- **Двуязычный интерфейс** (English / Русский)

---

### Инструкция по использованию

1. **Выберите способ задания области** на левой панели — загрузите shapefile или нарисуйте полигон на карте.
   - Используйте **только одно сельскохозяйственное поле** (один полигон).
2. **Задайте диапазон дат** — начальную и конечную даты. Рекомендуется и протестирован диапазон до одного года.
3. **Выберите модель** — ML PT-JPL или Original PT-JPL.
4. **Установите максимальный процент облачности** (меньшие значения дают более чистые снимки, но сокращают их количество).
5. **Нажмите «🚀 Запустить модель PT-JPL»** и дождитесь завершения обработки.
6. **Скачайте результаты**, используя кнопки, которые появятся после обработки:
   - TIFF-файлы (в виде ZIP-архива)
   - Метеорологические данные
   - Объединённый временной ряд в CSV
7. **Изучите карты** справа для анализа отдельных каналов и дат (в России иногда требуется запуск VPN для просмотра карт).

Для анализа **другого поля или другого года** просто повторите шаги выше с новыми входными данными. Каждый запуск независим.

---

### Выходные каналы (GeoTIFF)

| Канал | Описание |
|-------|----------|
| 1–7 | Спектральная отражательность Landsat (B1–B7) |
| 8 | Тепловой канал (ST_B10) |
| 9 | Поток скрытой теплоты LE (Вт/м²) |
| 10 | LE полога — LEc (Вт/м²) |
| 11 | LE почвы — LEs (Вт/м²) |
| 12 | Доля эвапотранспирации — ETrF |
| 13–14 | Доля LEc, доля LEs |
| 15–18 | Вегетационные индексы (IAVI, GLI, ExGR, SEVI) |
| 19 | ET — фактическая эвапотранспирация (мм/день) |
| 20 | ETc — транспирация (мм/день) |
| 21 | ETs — испарение почвы (мм/день) |

---

### Требования

- Python 3.9+
- Аккаунт Google Earth Engine с сервисным аккаунтом, настроенным в секретах Streamlit
- Зависимости: `streamlit`, `earthengine-api`, `geopandas`, `rasterio`, `folium`, `streamlit-folium`, `scipy`, `pandas`, `matplotlib`, `Pillow`, `branca`

---

### Настройка секретов (Streamlit Cloud)

Добавьте учётные данные сервисного аккаунта GEE в файл `.streamlit/secrets.toml`, если используете приложение локально:

```toml
[gee_service_account]
type = "service_account"
project_id = "ваш-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "ваш-сервисный-аккаунт@ваш-проект.iam.gserviceaccount.com"
client_id = "..."
```
