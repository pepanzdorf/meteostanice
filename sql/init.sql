CREATE SCHEMA srazkomer;
CREATE TABLE srazkomer.records (
    id SERIAL,
    inserted_at timestamp,
    temperature float,
    pressure float,
    rain integer,
    light integer
);