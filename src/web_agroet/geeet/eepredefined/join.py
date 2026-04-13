"""
Optional module to define some useful ee functions to join specific collections. 
"""
import ee

def set_datetime(img):
    """
    Adds a "datetime" property in the format YYYYMMDDTHH (e.g. 20150101T07)
    """
    d = img.get('system:time_start')
    d_parsed = ee.Date(d).format("yyyyMMdd'T'HH")
    img = img.set({'system:datetime': d_parsed})
    return img

def landsat_ecmwf(Sat_collection, Meteo_collection):
    sat_data = Sat_collection.map(set_datetime)
    met_data = Meteo_collection.map(set_datetime)

    # Join the two collections using the datetime property. 
    filterByDateTime = ee.Filter.equals(leftField='system:datetime', rightField='system:datetime')
    joinByDateTime = ee.ImageCollection(ee.Join.inner().apply(sat_data, met_data, filterByDateTime))
    def get_img(feature):
        return ee.Image.cat(feature.get('primary'), feature.get('secondary'))

    et_inputs = joinByDateTime.map(get_img)
    return et_inputs



def landsat_ecmwf_interp(Sat_collection, Meteo_collection):
    """
    Performs minute-level temporal interpolation of ERA5 hourly data
    to match Landsat acquisition times
    """

    sat_data = Sat_collection.map(set_datetime)
    met_data = Meteo_collection.map(set_datetime)

    def match_era5_to_landsat(landsat_img):
        landsat_date = ee.Date(landsat_img.get('system:time_start'))
        landsat_hour = landsat_date.get('hour')

        start_time = landsat_date.update(hour=landsat_hour, minute=0, second=0)
        end_time = start_time.advance(2, 'hour')

        era5_filtered = Meteo_collection.filterDate(start_time, end_time)

        era5_count = era5_filtered.size()
        has_both_hours = era5_count.gte(2)

        def interpolate_when_possible():

            era5_sorted = era5_filtered.sort('system:time_start')
            era1 = ee.Image(era5_sorted.first())
            era2 = ee.Image(ee.List(era5_sorted.toList(2)).get(1))

            t1 = ee.Date(era1.get('system:time_start'))
            t2 = ee.Date(era2.get('system:time_start'))
            t_target = landsat_date


            diff_total = t2.difference(t1, 'hour')
            diff1 = t2.difference(t_target, 'hour')
            diff2 = t_target.difference(t1, 'hour')


            w1 = diff1.divide(diff_total)
            w2 = diff2.divide(diff_total)

            # Perform weighted interpolation
            interpolated = era1.multiply(w1).add(era2.multiply(w2))

            return interpolated.copyProperties(landsat_img, ['system:time_start'])

        def use_nearest():
            # Find the nearest ERA5 image
            time_diff = ee.ImageCollection(Meteo_collection.map(lambda img:
                                                                img.set('time_diff',
                                                                        ee.Number(
                                                                            img.get('system:time_start')).subtract(
                                                                            landsat_date.millis()).abs())))

            nearest = time_diff.sort('time_diff').first()
            return ee.Image(nearest).copyProperties(landsat_img, ['system:time_start'])

        # Use conditional to decide which method to use
        result = ee.Algorithms.If(has_both_hours,
                                  interpolate_when_possible(),
                                  use_nearest())

        return ee.Image(result)

    # Map over all Landsat images
    matched_collection = sat_data.map(match_era5_to_landsat)

    filterByDateTime = ee.Filter.equals(leftField='system:time_start', rightField='system:time_start')
    joinByDateTime = ee.ImageCollection(ee.Join.inner().apply(sat_data, matched_collection, filterByDateTime))
    def get_img(feature):
        return ee.Image.cat(feature.get('primary'), feature.get('secondary'))

    et_inputs = joinByDateTime.map(get_img)
    return et_inputs






