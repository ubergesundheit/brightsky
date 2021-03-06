import datetime

from dateutil.tz import tzutc

from brightsky.parsers import (
    MOSMIXParser, PrecipitationObservationsParser, PressureObservationsParser,
    SunshineObservationsParser, TemperatureObservationsParser,
    WindObservationsParser)

from .utils import is_subset


def test_mosmix_parser(data_dir):
    p = MOSMIXParser(path=data_dir / 'MOSMIX_S.kmz')
    records = list(p.parse())
    assert len(records) == 240
    assert records[0] == {
        'observation_type': 'forecast',
        'source': 'MOSMIX:2020-03-13T09:00:00.000Z',
        'station_id': '01028',
        'lat': 19.02,
        'lon': 74.52,
        'height': 16.,
        'timestamp': datetime.datetime(2020, 3, 13, 10, 0, tzinfo=tzutc()),
        'temperature': 260.45,
        'wind_direction': 330.0,
        'wind_speed': 8.75,
        'precipitation': 0.1,
        'sunshine': None,
        'pressure_msl': 99000.0,
    }
    assert records[-1] == {
        'observation_type': 'forecast',
        'source': 'MOSMIX:2020-03-13T09:00:00.000Z',
        'station_id': '01028',
        'lat': 19.02,
        'lon': 74.52,
        'height': 16.,
        'timestamp': datetime.datetime(2020, 3, 23, 9, 0, tzinfo=tzutc()),
        'temperature': 267.15,
        'wind_direction': 49.0,
        'wind_speed': 7.72,
        'precipitation': None,
        'sunshine': None,
        'pressure_msl': 100630.0,
    }


def test_observations_parser_parses_metadata(data_dir):
    p = WindObservationsParser(path=data_dir / 'observations_recent_FF.zip')
    metadata = {
        'observation_type': 'recent',
        'source': (
            'Observations:Recent:produkt_ff_stunde_20180915_20200317_04911.txt'
        ),
        'station_id': '04911',
        'lat': 12.5597,
        'lon': 48.8275,
        'height': 350.5,
    }
    for record in p.parse():
        assert is_subset(metadata, record)


def test_observations_parser_handles_missing_values(data_dir):
    p = WindObservationsParser(path=data_dir / 'observations_recent_FF.zip')
    records = list(p.parse())
    assert records[5]['wind_direction'] == 90
    assert records[5]['wind_speed'] is None


def test_observations_parser_handles_location_changes(data_dir):
    p = WindObservationsParser(
        path=data_dir / 'observations_recent_FF_location_change.zip')
    records = list(p.parse())
    assert is_subset(
        {'lat': 12.5597, 'lon': 48.8275, 'height': 350.5}, records[0])
    assert is_subset(
        {'lat': 13.0, 'lon': 50.0, 'height': 345.0}, records[-1])


def _test_parser(cls, path, first, last, count=10, first_idx=0, last_idx=-1):
    p = cls(path=path)
    records = list(p.parse())
    first['timestamp'] = datetime.datetime.strptime(
        first['timestamp'], '%Y-%m-%d %H:%M').replace(tzinfo=tzutc())
    last['timestamp'] = datetime.datetime.strptime(
        last['timestamp'], '%Y-%m-%d %H:%M').replace(tzinfo=tzutc())
    assert len(records) == count
    assert is_subset(first, records[first_idx])
    assert is_subset(last, records[last_idx])


def test_temperature_observations_parser(data_dir):
    _test_parser(
        TemperatureObservationsParser,
        data_dir / 'observations_recent_TU.zip',
        {'timestamp': '2018-09-15 00:00', 'temperature': 286.85},
        {'timestamp': '2020-03-17 23:00', 'temperature': 275.75},
    )


def test_precipitation_observations_parser(data_dir):
    _test_parser(
        PrecipitationObservationsParser,
        data_dir / 'observations_recent_RR.zip',
        {'timestamp': '2018-09-22 20:00', 'precipitation': 0.0},
        {'timestamp': '2020-02-11 02:00', 'precipitation': 0.3},
    )


def test_wind_observations_parser(data_dir):
    _test_parser(
        WindObservationsParser,
        data_dir / 'observations_recent_FF.zip',
        {'timestamp': '2018-09-15 00:00',
         'wind_speed': 1.6, 'wind_direction': 80.0},
        {'timestamp': '2020-03-17 23:00',
         'wind_speed': 1.5, 'wind_direction': 130.0},
    )


def test_sunshine_observations_parser(data_dir):
    _test_parser(
        SunshineObservationsParser,
        data_dir / 'observations_recent_SD.zip',
        {'timestamp': '2018-09-15 11:00', 'sunshine': 600.},
        {'timestamp': '2020-03-17 16:00', 'sunshine': 0.},
        first_idx=2,
    )


def test_pressure_observations_parser(data_dir):
    _test_parser(
        PressureObservationsParser,
        data_dir / 'observations_recent_P0.zip',
        {'timestamp': '2018-09-15 00:00', 'pressure_msl': 98090.},
        {'timestamp': '2020-03-17 23:00', 'pressure_msl': 98980.},
    )
