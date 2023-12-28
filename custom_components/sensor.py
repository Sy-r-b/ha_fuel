import logging
import requests
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import track_time_interval
from datetime import datetime, timedelta
import datetime as dt

_LOGGER = logging.getLogger(__name__)
DOMAIN = "sainsburys_fuel"
ALLOWED_POSTCODES = ['DA', 'CT', 'TN', 'ME'] # CHANGE ME, only input the first 2 digits of required post codes.

# list of API's, add and delete as required.
# asconagroup commented out due to format causing errors.
api = [
    'https://api.sainsburys.co.uk/v1/exports/latest/fuel_prices_data.json',
    'https://storelocator.asda.com/fuel_prices_data.json',
    'https://www.bp.com/en_gb/united-kingdom/home/fuelprices/fuel_prices_data.json',
    'https://www.shell.co.uk/fuel-prices-data.html',
    'https://www.morrisons.com/fuel-prices/fuel.json',
    'https://applegreenstores.com/fuel-prices/data.json',
    'https://fuelprices.esso.co.uk/latestdata.json',
    'https://fuel.motorfuelgroup.com/fuel_prices_data.json',
    'https://www.rontec-servicestations.co.uk/fuel-prices/data/fuel_prices_data.json',
    'https://www.sgnretail.uk/files/data/SGN_daily_fuel_prices.json',
    #'https://fuelprices.asconagroup.co.uk/newfuel.json',
    'https://www.tesco.com/fuel_prices/fuel_prices_data.json',
    ]

api_data = {}

def api_update(now=None):
    # pulls data from each API and inputs into the api_data variable to prevent many API hits on sensor updates.
    global api_data
    for api_url in api:
        _LOGGER.info("Starting API data update: %s", api_url)
        try:
            if 'tesco' in api_url:
                headers = {
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
                }
                response = requests.get(api_url, headers=headers, timeout=15)
            
            else:
                response = requests.get(api_url, timeout=15)
            data = response.json()
            # Add data to the dictionary with the URL as the key
            api_data[api_url] = data
        except Exception as e:
            _LOGGER.error("Error updating data from API: %s", e)

def output_attributes(station):
    # checks if station input is in the allowed postcodes, then output the necessary attribute data.
    postcode = station.get('postcode', '').split()[0][:2]
    if postcode in ALLOWED_POSTCODES:
        brand = station.get('brand', '').replace("'", "")
        site_id = station.get('site_id', '')
        attributes = {
            'brand': brand,
            'site_id': site_id,
            'address': station.get('address', {}),
            'postcode': station.get('postcode', {}),
            'E10': station.get('prices', {}).get('E10', 0),
            'E5': station.get('prices', {}).get('E5', 0),
            'B7': station.get('prices', {}).get('B7', 0),
            'latitude': station.get('location', {}).get('latitude', 0),
            'longitude': station.get('location', {}).get('longitude', 0),
        }
        return attributes

def lowest_price(data, structure):
    lowest_value = float('1000')  # Start with a high value
    if None not in (data['E10'], data['E5'], data['B7']):
        # Check if this station has the lowest price
        for fuel_type in structure:
            if int(float(data[fuel_type])) == 0:
                _LOGGER.debug("Value was 0 or null, skipped")
            else:
                if int(float(structure[fuel_type]['price'])) > int(float(data[fuel_type])):
                    lowest_value = data[fuel_type]
                    structure[fuel_type]['price'] = lowest_value
                    structure[fuel_type]['site_id'] = data['site_id']
    return structure

def setup_platform(hass, config, add_entities, discovery_info=None):

    entities = []
    lowest_price_sensor = None
    api_update()
    try:
        for api_url in api:
            data = api_data[api_url]
            structure = {"E10": {"site_id": "", "price": 1000}, "E5": {"site_id": "", "price": 1000}, "B7": {"site_id": "", "price": 1000}}
            for station in data.get('stations', []):
                postcode = station.get('postcode', '').split()[0][:2]
                sensor_data = output_attributes(station)
                if sensor_data is None:
                    continue
                entity_id = f"{sensor_data['brand'].lower()}_fuel_{sensor_data['site_id'].lower()}_{sensor_data['postcode'].lower().split()[0][:2]}"
                entities.append(FuelSensor(hass, entity_id, sensor_data))
                hass.states.set(f"sensor.{entity_id}", "OK", sensor_data)
                _LOGGER.info("Sensor created: %s", entity_id)

                # Checks if the current station has the lowest price
                structure = lowest_price(sensor_data, structure)

            # for fuel_type in structure:
            #     for station in data.get('stations', []):
            #         if station['site_id'] == structure[fuel_type]['site_id']:
            #             brand = station.get('brand', '').replace("'", "")
            #             lowest_price_sensor_data = {
            #                 'brand': station.get('brand', ()),
            #                 'site_id': structure[fuel_type]['site_id'],
            #                 'postcode': station.get('postcode', {}),
            #                 'address': station.get('address', {}),
            #                 fuel_type: structure[fuel_type]['price'],
            #                 'latitude': station.get('location', {}).get('latitude', 0),
            #                 'longitude': station.get('location', {}).get('longitude', 0),
            #             }
            #             #hass.states.set(f"sensor.{brand}_lowest_{fuel_type}", "OK", lowest_price_sensor_data)
            #             lowest_price_sensor = FuelSensor(hass, f"{brand}_lowest_{fuel_type}", lowest_price_sensor_data)
            #             #entities.append(lowest_price_sensor)
            #             _LOGGER.info(f"Sensor created: {brand}_lowest_{fuel_type}")

    except Exception as e:
        _LOGGER.error("Error fetching data from API: %s", e)

    track_time_interval(hass, api_update, timedelta(hours=6)) # updates API data every 6 hours
    add_entities(entities)

class FuelSensor(Entity):
    def __init__(self, hass, entity_id, sensor_data):
        self._hass = hass
        self._entity_id = entity_id
        self._state = "OK"
        self._attributes = sensor_data

    @property
    def name(self):
        return self._entity_id

    @property
    def state(self):
        return self._state

    @property
    def should_poll(self):
        return True

    # @property
    # def update_interval(self):
    #     return timedelta(minutes=5)

    @property
    def device_state_attributes(self):
        return {
            'brand': self._attributes['brand'],
            'site_id': self._attributes['site_id'],
            'address': self._attributes['address'],
            'E10': self._attributes['E10'],
            'E5': self._attributes['E5'],
            'B7': self._attributes['B7'],
            'postcode': self._attributes['postcode'],
            'latitude': self._attributes['latitude'],
            'longitude': self._attributes['longitude'],
        }

    def update(self):
        _LOGGER.info("Sensor Update Begun: %s", self._entity_id)
        try:
            for api_url, data in api_data.items():
                structure = {"E10": {"site_id": "", "price": 1000}, "E5": {"site_id": "", "price": 1000}, "B7": {"site_id": "", "price": 1000}}
                for station in data.get('stations', []):
                    if station['site_id'] == self._attributes['site_id']:
                        new_attributes = output_attributes(station)
                        # Check if there's new data
                        if new_attributes != self._attributes:
                            self._attributes = new_attributes
                            self._state = "OK"
                            self._hass.states.set(f"sensor.{self._entity_id}", "OK", self._attributes)
                            _LOGGER.info("Sensor updated with new data %s", self._entity_id)
                            # Checks if the current station has the lowest price
                            structure = lowest_price(new_attributes, structure)

                        else:
                            _LOGGER.info("No new data for %s", self._entity_id)

                # for fuel_type in structure:
                #     for station in data.get('stations', []):
                #         if station['site_id'] == structure[fuel_type]['site_id']:
                #             brand = station.get('brand', '').replace("'", "")
                #             lowest_price_sensor_data = {
                #                 'brand': station.get('brand', ()),
                #                 'site_id': structure[fuel_type]['site_id'],
                #                 'postcode': station.get('postcode', {}),
                #                 'address': station.get('address', {}),
                #                 fuel_type: structure[fuel_type]['price'],
                #                 'latitude': station.get('location', {}).get('latitude', 0),
                #                 'longitude': station.get('location', {}).get('longitude', 0),
                #             }
                #             hass.states.set(f"sensor.{brand}_lowest_{fuel_type}", "OK", lowest_price_sensor_data)
                #             #lowest_price_sensor = FuelSensor(hass, f"{brand}_lowest_{fuel_type}", lowest_price_sensor_data)
                #             #entities.append(lowest_price_sensor)
                #             _LOGGER.info(f"Sensor created: {brand}_lowest_{fuel_type}")
        except Exception as e:
            _LOGGER.error("Error updating data for API: %s", e)
