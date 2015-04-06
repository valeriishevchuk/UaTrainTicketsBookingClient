import requests
import json
import execjs
import re

from collections import namedtuple
from enum import Enum
from datetime import datetime


class BadResponseException(Exception):
    pass


Station = namedtuple('Station', 'id name')
Train = namedtuple('Train', 'name, from_station, from_time, till_station, till_time, free_seats')


class CarType(Enum):
    suite = ('Suite / first-class sleeper', 'Л')
    coupe = ('Coupe / coach with compartments', 'К')
    berth = ('Berth / third-class sleeper', 'П')
    common = ('Common / day coach', 'О')
    seating1 = ('Seating first class', 'С1')
    seating2 = ('Seating second class', 'С2')

    @staticmethod
    def type_by_letter(letter):
        for car_type in CarType:
            if car_type.value[1] == letter:
                return car_type

        raise 'Can\'t find enum for leter'


class Client:
    __base_address = 'http://booking.uz.gov.ua/en/'
    __purchase_url = 'purchase/'

    def __parse_cookie(self, headers_str):
        for cookie in headers_str.split(';'):
            if cookie.startswith('_gv_sessid'):
                self.__cookie_value = cookie + ';'


    def __parse_token(self, html_str):
        pattern = re.compile('\\$\\$_=.*~\\[\\];.*\"\"\\)\\(\\)\\)\\(\\);')
        match = pattern.search(html_str)
        
        if not match:
            raise "Can't find obfuscated tocken data."
        
        obfuscated = match.group()

        ctx = execjs.compile("""
            function getToken() {
                var token = null;
                localStorage = {
                    setItem:    function(key, value) {
                                    if (key === 'gv-token')
                                        token=value
                             }
                };
            """ +
            obfuscated +
            """
                return token;
            }"""
        )
        self.__token_value = ctx.call('getToken')


    def __init__(self):
        r = requests.get(self.__base_address)
        self.__parse_cookie(r.headers['Set-Cookie'])
        self.__parse_token(r.text)
        

    def __build_payload_for_search(self, station1, station2, date):
        payload = {}
        payload['station_id_from'] = station1['id']
        payload['station_id_till'] = station2['id']
        payload['date_dep'] = date
        payload['time_dep'] = '00:00'
        payload['time_dep_till'] = '24:00'
        return payload

    
    def __build_headers(self):
        headers = {}
        headers['Cookie'] = self.__cookie_value
        headers['GV-Token'] = self.__token_value
        headers['GV-Ajax'] = '1'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers['Referer'] = self.__base_address
        return headers

    
    def __build_free_seats_from_data(self, json_data):
        seats = {}
        for type_data in json_data['types']:
            seats[CarType.type_by_letter(type_data['letter'])] = int(type_data['places'])
        return seats


    def find_stations(self, name):
        station_url = 'station/'
        full_url = self.__base_address + self.__purchase_url + station_url + name
        r = requests.post(full_url)
        data = json.loads(r.text)

        if data['error']:
            raise BadResponseException(data['value'])

        stations = []
        for station_data in data['value']:
            stations.append(Station(id=station_data['station_id'], name=station_data['title']))

        return stations


    def find_tickets(self, station1, station2, date):
        search_url = 'search/'
        
        full_url = self.__base_address + self.__purchase_url + search_url
        payload = self.__build_payload_for_search(station1, station2, date)
        
        r = requests.post(full_url, data=payload, headers=self.__build_headers())
        data = json.loads(r.text)

        if data['error']:
            raise BadResponseException(data['value'])

        trains = []
        for train_data in data['value']:
            train = Train(
                        name=train_data['num'],
                        from_station=Station(id=train_data['from']['station_id'], name=train_data['from']['station']),
                        till_station=Station(id=train_data['till']['station_id'], name=train_data['till']['station']),
                        from_time=datetime.fromtimestamp(train_data['from']['date']),
                        till_time=datetime.fromtimestamp(train_data['till']['date']),
                        free_seats=self.__build_free_seats_from_data(train_data)
                    )
            trains.append(train)

        return trains
