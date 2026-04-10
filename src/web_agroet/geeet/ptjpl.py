"""
This module contains functions to run the PT-JPL crop water use model.

The model functions are hybrid: they work both with numpy arrays or ee.Images*:
If the instance of the input is recognized as an ee.Image, the output is
computed as an ee.Image as well.
Otherwise, it is computed as a numpy array.

To reduce the dependencies of this package, 
the ee capabilities are optional. That means that 
in order to use the ee capabilities, the user must install the ee package:

conda install -c conda-forge earthengine-api
or 
pip install earthengine-api

*Exceptions:
    add_fapar - function intended only for ee.Images

References can be found at the end of this module
They can be printed in python using the following two functions:
geeet.ptjpl.cite() - main reference for this module
geeet.ptjpl.cite_all() - all references used for this module
"""

from src.web_agroet.geeet.common import is_img
try: 
    import ee
except Exception:
    pass


def ptjpl_arid(img=None, # ee.Image with inputs as bands (takes precedence over numpy arrays)
    Ta=None,  P=None, NDVI=None, F_aparmax=None,
    LAI = None, # optional; computed using NDVI if LAI is not available.
    Rn=None, Sdn=None, Ldn=None, Tr=None, Alb = None,  # net radiation OR Sdn, Ldn, Tr, and Albedo 
    G = None, # optional; computed if not provided. 
    RH=None, Td=None, # relative humidity OR dewpoint temperature (if RH not provided)
    doy=None, time=None, utc_offset=None, longitude=None, latitude=None,
    AlphaPT=1.26, # Default Priestly-Taylor coefficient for canopy potential transpiration
    G_params = [0.31, 74000, 10800], k_par = 0.5, k_rns = 0.6, Beta = 1.0, 
    Mask=1.0, Mask_Val=0.0, Vza = 0,
    Rn_calc=True):
    '''
    Function to compute evapotranspiration components using the PT-JPL model
    adapted for arid lands (Aragon et al., 2018)

    Inputs ([] denotes an optional input that is computed if not provided.
            {} denotes an optional input that is required if the previous [] was not provided)
    img: ee.Image with the following bands (or image properties):
        - air_temperature : air temperature in Kelvin.
        - surface_pressure : Pressure in Pa.
        - NDVI : Normalized Difference Vegetation Index values.
        - [LAI]: Leaf area index (m2/m2) (computed using NDVI if not provided)
        - fapar_max : Maximum fapar* values.
        - [net_radiation]: Net radiation in W/m2 (Computed if not provided - see geeet.solar.compute_Rn)
        - {solar_radiation}: Downwelling shortwave radiation in W/m2 (Required if net_radiation is not found)
        - {thermal_radiation}: Downwelling longwave radiation in W/m2 (Required if net_radiation is not found)
        - {radiometric_temperature}: Surface temperature in K (Required if net_radiation is not found) 
        - {albedo}: shortwave broadband albedo (Required if net_radiation is not found)
        - [relative_humidity]: relative humidity (%) (computed if not provided - see geeet.meteo.relative_humidity)
        - {dewpoint_temperature}:  dewpoint temperature (K) (Required if relative_humidity is not provided)
        - [ground_heat_flux]: Ground heat flux, in W/m2 (optional; computed if not provided)
        - doy (ee.Image property): Day of year. 
        - time (ee.Image property): Local time of observation (decimal)    
    or: numpy arrays as keyword parameters (all of these are ignored if img is an ee.Image):
        - Ta: air temperature in Kelvin
        - P: surface pressure in Pa
        - NDVI: NDVI values
        - [LAI]: Leaf area index (m2/m2) (optional)
        - F_aparmax: Maximum fapar* values
        - [Rn]: net radiation in W/m2]. Alternatively:
            {Sdn}: Downwelling shortwave radiation in W/m2,
            {Ldn}: Downwelling longwave radiation in W/m2,
            {Tr}: radiometric temperature in K
            {Alb}: albedo
        - [RH]: relative humidity (%). Alternatively:
            {Td}: dewpoint temperature in K
        - doy: day of year
        - time: local time of observation (decimal)
        - longitude: longitude for each observation

        *Fraction of the photosynthetic active radiation (PAR) absorbed by green vegetation cover.

    Optional_Inputs: 
        - AlphaPT (float): Priestley-Taylor alpha coefficient
        - G_params (list [float A, float B, float C]): the parameters for
          computing solid heat flux (Santanello and Friedl, 2003)
          where A is the maximum ratio of G/Rns
          B reduces deviation of G/Rn to measured values, also thought of
          as the spread of the cosine wave and C is the phase shift between
          the peaks of Rns and G. B and C are in seconds.        
        - k_par (float): parameter used in the computation of LAI (see compute_lai) 
        - k_rns (float): parameter used to partition net radiation to soil 
                         (see geeet.vegetation.compute_rns)
        - Beta (float): Sensibility parameter to VPD in kPa (see compute_fsm)
        - Mask (numpy array): an array containing the coded invalid data (e.g. -9999)
            of the same size as the input image. Only for numpy array inputs; ignored for
            ee.Image inputs.
        - Mask_Val (number): the value that represents invalid data. Only for numpy array
            inputs; ignored for ee.Image inputs. 
        - band_names (list of strings): If provided, the bands in the output ee.Image
                are renamed using this list. Ignored if inputs are numpy arrays.            

    Outputs: 
        - ET (dictionary or ee.Image): dictionary containing numpy arrays with the following
                                  components, or the following bands are added to the input image:
        -     LE: the latent heat flux.
        -     LEc: the canopy transpiration component of LE.
        -     LEs: the soil evaporation component of LE.
        -     LEi: the interception evaporation component of LE.
        -     H: the sensible heat flux.
        -     G: the ground heat flux.
        -     Rn: the net radiation.
    '''
    import numpy as np
    from src.web_agroet.geeet.vegetation import (compute_Rns, compute_lai, compute_fwet,
        compute_fg, compute_ft_arid, compute_fapar, compute_fm, 
        compute_fsm, compute_ftheta)
    from src.web_agroet.geeet.solar import (compute_g, compute_Rn, compute_d2, compute_W, compute_tsw,
                                         compute_Rs, compute_Rlu, compute_Rld, compute_emis_atm, compute_emis_0,
                                         compute_Rln, compute_solar_angles)
    from src.web_agroet.geeet.meteo import relative_humidity, compute_met_params

    band_names = img.bandNames()
    NDVI = img.select('NDVI')
    Ta = img.select('air_temperature')
    Td = img.select('dewpoint_temperature')
    P = img.select('surface_pressure')
    F_aparmax = ee.Image(0.95)
    time = img.get('time')
    doy = img.get('doy')
    latitude = img.get('latitude')
    longitude = img.get('longitude')


    LAI = ee.Algorithms.If(band_names.contains('LAI'), img.select('LAI'),
                           compute_lai(NDVI, k_par, band_name = 'LAI'))
    LAI = ee.Image(LAI)

    RH = ee.Algorithms.If(band_names.contains('relative_humidity'), img.select('relative_humidity'),\
        relative_humidity(Ta, img.select('dewpoint_temperature')))
    RH = ee.Image(RH)

    f_theta = compute_ftheta(LAI, theta=Vza)

    if Rn_calc:

        doy = ee.Number(doy)
        time = ee.Number(time)
        utc_offset = ee.Number(utc_offset)
        time_local = time.add(utc_offset).mod(24)
        latitude = ee.Number(latitude)

        d2 = ee.Image(compute_d2(doy))
        P_kPa = ee.Image(0.001).multiply(P)
        met_params = compute_met_params(Ta, Td, P)
        ea = met_params.select('ea')
        ea_kPa = ee.Image(0.001).multiply(ea)
        W = compute_W(ea_kPa, P_kPa)

        solar_angles = compute_solar_angles(doy=doy, time=time_local, latitude=latitude)
        cos_incidence = ee.Image(solar_angles.select('cos_incidence'))

        tsw = compute_tsw(P_kPa, W, cos_incidence)
        Rs = compute_Rs(cos_incidence, tsw, d2)
        Rsn = (ee.Image(1).subtract(img.select('albedo'))).multiply(Rs)
        Rlu = compute_Rlu(img.select('radiometric_temperature'), f_theta)
        emis_atm = compute_emis_atm(tsw)
        emis_0 = compute_emis_0(LAI)
        Rld = compute_Rld(Ta, emis_atm)
        Rln = compute_Rln(Rlu, Rld,emis_0)
        Rn = Rsn.add(Rln)


    else:
        Rn_short = (ee.Image(1).subtract(img.select('albedo'))).multiply(img.select('solar_radiation'))
        Rn_long = img.select('net_thermal_radiation')
        Rn = Rn_short.add(Rn_long)

    Rn = ee.Image(Rn)

    rns = compute_Rns(Rn, LAI, k=k_rns, use_zenith = False)

    G = ee.Algorithms.If(band_names.contains('ground_heat_flux'), img.select('ground_heat_flux'), \
        compute_g(doy = doy, time=time, Rns = rns, G_params = G_params))
    G = ee.Image(G)

    # all of these functions work for both ee.Images and numpy arrays:
    fwet = compute_fwet(RH)
    fg = compute_fg(NDVI)
    ft = compute_ft_arid(Ta)
    f_apar = compute_fapar(NDVI)
    fm = compute_fm(f_apar, F_aparmax)
    met_params = compute_met_params(Ta, Td, P)
    fsm = compute_fsm(RH, Ta, Beta)


    taylor = met_params.select('taylor').multiply(AlphaPT)
    rnc = Rn.subtract(rns)
    cst_1 = ee.Image(1.0)
    fwet_sub1 = cst_1.subtract(fwet)
    # Canopy transpiration image
    LEc = fwet_sub1.multiply(fg).multiply(ft).multiply(fm).multiply(taylor).multiply(rnc).rename('LEc')
    # Soil evaporation image
    LEs = ((fwet_sub1.multiply(fsm)).add(fwet)).multiply(taylor).multiply(rns.subtract(G)).rename('LEs')
    # Interception evaporation image
    LEi = fwet.multiply(taylor).multiply(rnc).rename('LEi')
    # Evapotranspiration image
    LE = LEc.add(LEs).add(LEi).rename('LE')

    # Compute the sensible heat flux image H by residual
    H = (Rn.subtract(G)).subtract(LE).rename('H')
    Rn = rns.add(rnc).rename('Rn')


    # Add the outputs to the input image:
    # LE, LEc, LEs, LEi, H, G
    G = G.rename('G')
    doy = ee.Image(doy).rename('doy')
    time = ee.Image(time).rename('time')

    ET = img.addBands(RH).addBands(LE).addBands(LEc).addBands(LEs).addBands(LEi).addBands(H).addBands(G).addBands(Rn)

    return ET

