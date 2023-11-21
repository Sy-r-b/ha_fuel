import logging
import requests
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import device_registry as dr
from datetime import datetime
import datetime as dt  # Add this line

_LOGGER = logging.getLogger(__name__)
DOMAIN = "sainsburys_fuel"
ALLOWED_POSTCODES = ['PO', 'ST', 'CO', 'DE']
api = [
    'https://api.sainsburys.co.uk/v1/exports/latest/fuel_prices_data.json',
    'https://storelocator.asda.com/fuel_prices_data.json',
    ]

def lowest_price(data, structure):
    lowest_value = float('1000')  # Start with a high value
    if None not in (data['E10'], data['E5'], data['B7']):
        # Check if this station has the lowest price
        for fuel_type in structure:
            if int(float(structure[fuel_type]['price'])) > int(float(data[fuel_type])):
                lowest_value = data[fuel_type]
                structure[fuel_type]['price'] = lowest_value
                structure[fuel_type]['site_id'] = data['site_id']

    # You might want to return or use the updated structure here
    return structure

def setup_platform(hass, config, add_entities, discovery_info=None):
    entities = []
    lowest_price_sensor = None
    try:
        for api_url in api:
            response = requests.get(api_url)
            data = response.json()
            structure = {"E10": {"site_id": "", "price": 1000}, "E5": {"site_id": "", "price": 1000}, "B7": {"site_id": "", "price": 1000}}

            for station in data.get('stations', []):
                site_id = station.get('site_id', '')
                brand = station.get('brand', '').replace("'", "")
                postcode = station.get('postcode', '').split()[0][:2]
                if postcode in ALLOWED_POSTCODES:
                    entity_id = f"{brand.lower()}_fuel_{site_id.lower()}_{postcode.lower()}"
                    sensor_data = {
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
                    entities.append(SainsburysFuelSensor(hass, entity_id, sensor_data))
                    hass.states.set(f"sensor.{entity_id}", "OK", sensor_data)
                    
                    _LOGGER.info("Sensor created: %s", entity_id)

                    structure = lowest_price(sensor_data, structure)

            for fuel_type in structure:
                for station in data.get('stations', []):
                    if station['site_id'] == structure[fuel_type]['site_id']:
                        brand = station.get('brand', '').replace("'", "")
                        lowest_price_sensor_data = {
                            'brand': station.get('brand', ()),
                            'site_id': structure[fuel_type]['site_id'],
                            'postcode': station.get('postcode', {}),
                            'address': station.get('address', {}),
                            fuel_type: structure[fuel_type]['price'],
                            'latitude': station.get('location', {}).get('latitude', 0),
                            'longitude': station.get('location', {}).get('longitude', 0),
                        }
                        hass.states.set(f"sensor.{brand}_lowest_{fuel_type}", "OK", lowest_price_sensor_data)
                        lowest_price_sensor = SainsburysFuelSensor(hass, f"{brand}_lowest_{fuel_type}", lowest_price_sensor_data)
                        entities.append(lowest_price_sensor)
                        _LOGGER.info(f"Sensor created: {brand}_lowest_{fuel_type}")

    except Exception as e:
        _LOGGER.error("Error fetching data from API: %s", e)

class SainsburysFuelSensor(Entity):
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
        return False

    @property
    def update_interval(self):
        return timedelta(minutes=5)

    @property
    def device_state_attributes(self):
        return {
            'brand': brand,
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
        _LOGGER.info("Update Begun")
        try:
            for api_url in api:
                response = requests.get(api_url)
                data = response.json()
                structure = {"E10": {"site_id": "", "price": 1000}, "E5": {"site_id": "", "price": 1000}, "B7": {"site_id": "", "price": 1000}}
                for station in data.get('stations', []):
                    site_id = station.get('site_id', '')
                    postcode = station.get('postcode', '').split()[0][:2]
                    brand = station.get('brand', '').replace("'", "")
                    _LOGGER.info("Sensor Update Begun: %s", self._entity_id)
                    if postcode in ALLOWED_POSTCODES and self._entity_id.endswith(f"{site_id.lower()}_{postcode.lower()}"):
                        self._attributes = {
                            'brand': brand,
                            'postcode': station.get('postcode', {}),
                            'address': station.get('address', {}),
                            'E10': station.get('prices', {}).get('E10', 0),
                            'E5': station.get('prices', {}).get('E5', 0),
                            'B7': station.get('prices', {}).get('B7', 0),
                            'latitude': station.get('location', {}).get('latitude', 0),
                            'longitude': station.get('location', {}).get('longitude', 0),
                        }
                        self._state = "OK"
                        self._hass.states.set(f"sensor.{self._entity_id}", "OK", self._attributes)
                        self._hass.async_schedule_update_ha_state()
                        _LOGGER.info("Sensor updated: %s", self._entity_id)

                for fuel_type in structure:
                    for station in data.get('stations', []):
                        if station['site_id'] == structure[fuel_type]['site_id']:
                            brand = station.get('brand', '').replace("'", "")
                            lowest_price_sensor_data = {
                                'brand': station.get('brand', ()),
                                'site_id': structure[fuel_type]['site_id'],
                                'postcode': station.get('postcode', {}),
                                'address': station.get('address', {}),
                                fuel_type: structure[fuel_type]['price'],
                                'latitude': station.get('location', {}).get('latitude', 0),
                                'longitude': station.get('location', {}).get('longitude', 0),
                            }
                            hass.states.set(f"sensor.{brand}_lowest_{fuel_type}", "OK", lowest_price_sensor_data)
                            lowest_price_sensor = SainsburysFuelSensor(hass, f"{brand}_lowest_{fuel_type}", lowest_price_sensor_data)
                            entities.append(lowest_price_sensor)
                            _LOGGER.info(f"Sensor created: {brand}_lowest_{fuel_type}")

        except Exception as e:
            _LOGGER.error("Error updating data for Sainsbury's API: %s", e)