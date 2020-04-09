# BrightSky

Facilitating easy access to weather records and forecasts by Deutscher
Wetterdienst.


## Meteorological Elements

| Column               | Unit    | Element
| -------------------- | :-----: | --------------------------------------------
| `temperature`        | K       | Air temperature, 2 m above ground
| `precipitation`      | kg / m² | Precipitation during last hour
| `wind_speed`         | m / s   | Wind speed, average during last hour
| `wind_direction`     | °       | Wind direction, dominant during last hour
| `pressure_msl`       | Pa      | Barometric pressure at mean sea level
| `sunshine`           | s       | Sunshine duration during last hour

## Running in containers

- `docker-compose up -d database` to start a local database. It will store its data in a local directory
- `docker-compose run --rm brightsky migrate` to apply database migrations
- `docker-compose run --rm brightsky poll --enqueue` to fill up the worker queue
- `docker-compose run --rm -d brightsky work` to start workers in background
