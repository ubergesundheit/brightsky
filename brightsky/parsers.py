import csv
import datetime
import io
import logging
import re
import zipfile

import dateutil.parser
from dateutil.tz import tzutc
from parsel import Selector

from brightsky.utils import cache_path, download


logger = logging.getLogger(__name__)


class Parser:

    DEFAULT_URL = None

    def __init__(self, path=None, url=None):
        self.url = url or self.DEFAULT_URL
        self.path = path
        if not self.path and self.url:
            self.path = cache_path(self.url)

    def download(self):
        download(self.url, self.path)


class MOSMIXParser(Parser):

    DEFAULT_URL = (
        'https://opendata.dwd.de/weather/local_forecasts/mos/MOSMIX_S/'
        'all_stations/kml/MOSMIX_S_LATEST_240.kmz')

    ELEMENTS = {
        'TTT': 'temperature',
        'DD': 'wind_direction',
        'FF': 'wind_speed',
        'RR1c': 'precipitation',
        'SunD1': 'sunshine',
        'PPPP': 'pressure_msl',
    }

    def parse(self):
        sel = self.get_selector()
        timestamps = self.parse_timestamps(sel)
        source = self.parse_source(sel)
        logger.debug(
            'Got %d timestamps for source %s', len(timestamps), source)
        station_selectors = sel.css('Placemark')
        for i, station_sel in enumerate(station_selectors):
            logger.debug(
                'Parsing station %d / %d', i+1, len(station_selectors))
            yield from self.parse_station(station_sel, timestamps, source)

    def get_selector(self):
        with zipfile.ZipFile(self.path) as zf:
            infolist = zf.infolist()
            assert len(infolist) == 1, f'Unexpected zip content in {self.path}'
            with zf.open(infolist[0]) as f:
                sel = Selector(f.read().decode('latin1'), type='xml')
        sel.remove_namespaces()
        return sel

    def parse_timestamps(self, sel):
        return [
            dateutil.parser.parse(ts)
            for ts in sel.css('ForecastTimeSteps > TimeStep::text').extract()]

    def parse_source(self, sel):
        return ':'.join(sel.css('ProductID::text, IssueTime::text').extract())

    def parse_station(self, station_sel, timestamps, source):
        station_id = station_sel.css('name::text').extract_first()
        lat, lon, height = station_sel.css(
            'coordinates::text').extract_first().split(',')
        records = {'timestamp': timestamps}
        for element, column in self.ELEMENTS.items():
            values_str = station_sel.css(
                f'Forecast[elementName="{element}"] value::text'
            ).extract_first()
            records[column] = [
                None if row[0] == '-' else float(row[0])
                for row in csv.reader(
                    re.sub(r'\s+', '\n', values_str.strip()).splitlines())
            ]
            assert len(records[column]) == len(timestamps)
        base_record = {
            'observation_type': 'forecast',
            'source': source,
            'station_id': station_id,
            'lat': float(lat),
            'lon': float(lon),
            'height': float(height),
        }
        # Turn dict of lists into list of dicts
        yield from (
            {**base_record, **dict(zip(records, row))}
            for row in zip(*records.values())
        )


class ObservationsParser(Parser):

    elements = {}
    conversion_factors = {}

    def parse(self):
        with zipfile.ZipFile(self.path) as zf:
            station_id = self.parse_station_id(zf)
            lat_lon_history = self.parse_lat_lon_history(zf, station_id)
            yield from self.parse_records(zf, station_id, lat_lon_history)

    def parse_station_id(self, zf):
        for filename in zf.namelist():
            if (m := re.match(r'Metadaten_Geographie_(\d+)\.txt', filename)):
                return m.group(1)
        raise ValueError(f"Unable to parse station ID for {self.path}")

    def parse_lat_lon_history(self, zf, station_id):
        with zf.open(f'Metadaten_Geographie_{station_id}.txt') as f:
            reader = csv.DictReader(
                io.TextIOWrapper(f, encoding='latin1'),
                delimiter=';')
            history = {}
            for row in reader:
                date_from = datetime.datetime.strptime(
                    row['von_datum'].strip(), '%Y%m%d'
                ).replace(tzinfo=tzutc())
                history[date_from] = (
                    float(row['Geogr.Laenge']),
                    float(row['Geogr.Breite']),
                    float(row['Stationshoehe']))
            return history

    def parse_records(self, zf, station_id, lat_lon_history):
        product_filenames = [
            fn for fn in zf.namelist() if fn.startswith('produkt_')]
        assert len(product_filenames) == 1, "Unexpected product count"
        filename = product_filenames[0]
        with zf.open(filename) as f:
            reader = csv.DictReader(
                io.TextIOWrapper(f, encoding='latin1'),
                delimiter=';')
            for row in reader:
                timestamp = datetime.datetime.strptime(
                    row['MESS_DATUM'], '%Y%m%d%H').replace(tzinfo=tzutc())
                for date, lat_lon_height in lat_lon_history.items():
                    if date > timestamp:
                        break
                    lat, lon, height = lat_lon_height
                yield {
                    'observation_type': 'recent',
                    'source': f'Observations:Recent:{filename}',
                    'station_id': station_id,
                    'lat': lat,
                    'lon': lon,
                    'height': height,
                    'timestamp': timestamp,
                    **self.parse_elements(row),
                }

    def parse_elements(self, row):
        elements = {
            element: (
                float(row[element_key])
                if row[element_key].strip() != '-999'
                else None)
            for element, element_key in self.elements.items()
        }
        for element, factor in self.conversion_factors.items():
            elements[element] *= factor
            elements[element] = round(elements[element], 2)
        return elements


class TemperatureObservationsParser(ObservationsParser):

    elements = {
        'temperature': 'TT_TU',
    }

    def parse_elements(self, row):
        elements = super().parse_elements(row)
        # Convert °C to K
        elements['temperature'] = round(elements['temperature'] + 273.15, 2)
        return elements


class PrecipitationObservationsParser(ObservationsParser):

    elements = {
        'precipitation': '  R1',
    }


class WindObservationsParser(ObservationsParser):

    elements = {
        'wind_speed': '   F',
        'wind_direction': '   D',
    }


class SunshineObservationsParser(ObservationsParser):

    elements = {
        'sunshine': 'SD_SO',
    }
    conversion_factors = {
        # Minutes to seconds
        'sunshine': 60,
    }


class PressureObservationsParser(ObservationsParser):

    elements = {
        'pressure_msl': '  P0',
    }
    conversion_factors = {
        # hPa to Pa
        'pressure_msl': 100,
    }
