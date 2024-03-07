CREATE SCHEMA weatherstation;
CREATE TABLE weatherstation.records (
    id SERIAL,
    inserted_at timestamp,
    temperature_bmp280 float,
    pressure_bmp280 float,
    rain integer,
    light_temt6000 integer,
    light_bh1750 float,
    solar int,
    humidity_dht float,
    temperature_ds18b20 float,
    station_name text,
    temperature_dht float,
    anemometer int,
    rain_check int
);