import numpy as np

def teten(Td):
    a1 = 611.21 # in Pa
    a3 = 17.502
    a4 = 32.19 # in K
    T0 = 273.16 # in K
    ea = a1*np.exp(a3*(Td-T0)/(Td-a4))
    ea = ea*0.001
    return ea

def relative_humidity(temperature, dewpoint_temperature):
    ea = teten(dewpoint_temperature)
    esat = teten(temperature)
    RH = 100*ea/esat
    return RH

def get_elevation(lat, lon):
    """Get elevation from Open-Meteo API (free, no API key)."""
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
    response = requests.get(url)
    return response.json()['elevation'][0]