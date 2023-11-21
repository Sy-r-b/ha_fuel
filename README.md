# ha_fuel
This custom integration will create fuel sensors for each API within your defined postcodes.

Each sensor will contain the following attributes per station:
    Brand
    Site ID
    Address
    Postcode
    E10 price
    E5 price
    B7 price
    Latitude
    Longitude

The longitude and latitude attributes were necessary to be able to place the sensors on map cards, if needed.

This is still very incomplete, and have used ChatGPT to help me create this as I am very much not a coder, with a few issues including the sensors not updating on a regular basis.

This will create A LOT of sensors depending on how many postcodes you have.