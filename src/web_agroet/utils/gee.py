import ee

def get_one_per_day(collection):
    # Get unique dates
    dates = collection.aggregate_array('system:time_start') \
        .map(lambda t: ee.Date(t).format('YYYY-MM-dd')) \
        .distinct()

    # For each unique date, take the first image
    def get_first_image(date_str):
        date = ee.Date(date_str)
        start = date
        end = date.advance(1, 'day')

        # Filter collection to that day and get first image
        daily_images = collection.filterDate(start, end)
        return ee.Image(daily_images.first())

    # Create new collection with one image per day
    unique_list = dates.map(get_first_image)
    return ee.ImageCollection(unique_list)