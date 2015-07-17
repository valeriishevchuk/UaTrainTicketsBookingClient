import requests
import json
import execjs
import re

from collections import namedtuple, defaultdict
from enum import Enum
from datetime import datetime


class BadResponseException(Exception):
    pass


Station = namedtuple('Station', 'id name')
Train = namedtuple('Train', 'name, from_station, from_time, till_station, till_time, free_seats')
CoachInfo = namedtuple('CoachInfo', 'number has_bedding free_places book_price services c_class type_id')


class CoachType(Enum):
    suite = ('Suite / first-class sleeper', 'Л')
    coupe = ('Coupe / coach with compartments', 'К')
    berth = ('Berth / third-class sleeper', 'П')
    common = ('Common / day coach', 'О')
    seating1 = ('Seating first class', 'С1')
    seating2 = ('Seating second class', 'С2')

    @staticmethod
    def type_by_letter(letter):
        for car_type in CoachType:
            if car_type.value[1] == letter:
                return car_type

        raise 'Can\'t find enum for leter'


class CoachService(Enum):
    tea = ('Tea', 'Ш')
    double_tea = ('Double-tea', 'Ч')
    foodset = ('Foodset', 'Х')

    @staticmethod
    def type_by_letter(letter):
        for coach_service in CoachService:
            if coach_service.value[1] == letter:
                return coach_service

        raise 'Can\'t find CoachService for letter'


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
        return payload


    def __build_payload_for_coaches_info(self, train, coach_type):
        payload = {}
        payload['station_id_from'] = train.from_station.id
        payload['station_id_till'] = train.till_station.id
        payload['train'] = train.name
        payload['coach_type'] = coach_type.value[1]
        payload['date_dep'] = int(train.from_time.timestamp())
        return payload
    
    
    def __build_payload_for_coach_info(self, train, coach_info_json):
        payload = {}
        payload['station_id_from'] = train.from_station.id
        payload['station_id_till'] = train.till_station.id
        payload['train'] = train.name
        payload['date_dep'] = int(train.from_time.timestamp())
        payload['coach_num'] = coach_info_json['num']
        payload['coach_class'] = coach_info_json['coach_class']
        payload['coach_type_id'] = coach_info_json['coach_type_id']
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
            seats[CoachType.type_by_letter(type_data['letter'])] = int(type_data['places'])
        return seats


    def __build_coach_info_from_data(self, coach_info_json, free_places_info_json):
        places = []
        for price_cat in coach_info_json['prices']:
            places.append((tuple(map(int, free_places_info_json[price_cat])), int(coach_info_json['prices'][price_cat])))

        return CoachInfo(
                        number=coach_info_json['num'],
                        has_bedding=coach_info_json['hasBedding'],
                        free_places=places,
                        book_price=coach_info_json['reserve_price'],
                        services=[CoachService.type_by_letter(s) for s in coach_info_json['services']],
                        c_class=coach_info_json['coach_class'],
                        type_id=coach_info_json['coach_type_id']
                    )


    def __perform_purchase_request(self, sub_url, payload):
        full_url = self.__base_address + self.__purchase_url + sub_url
        r = requests.post(full_url, data=payload, headers=self.__build_headers())
        data = r.json()

        if data['error']:
            raise BadResponseException(data['value'])

        return data['value']


    def find_stations(self, name):
        try:
            response_data = self.__perform_purchase_request('station/' + name, {})
        except BadResponseException:
            return []

        stations = []
        for station_data in response_data:
            stations.append(Station(id=station_data['station_id'], name=station_data['title']))

        return stations


    def find_trains(self, station1, station2, date):
        try:
            payload = self.__build_payload_for_search(station1, station2, date)
            response_data = self.__perform_purchase_request('search/', payload)
        except BadResponseException:
            return []

        trains = []
        for train_data in response_data:
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


    def coaches_info_for_train(self, train):
        coaches_info = defaultdict(list) 

        for coach_type in train.free_seats:
            try:
                payload = self.__build_payload_for_coaches_info(train, coach_type)
                response_data = self.__perform_purchase_request('coaches/', payload)
            except BadResponseException:
                continue

            for coach_info_json in response_data['coaches']:
                try:
                    payload = self.__build_payload_for_coach_info(train, coach_info_json)
                    response_data = self.__perform_purchase_request('coach/', payload)
                except BadResponseException:
                    continue

                coach_info = self.__build_coach_info_from_data(coach_info_json, response_data['places'])
                coaches_info[coach_type].append(coach_info)

        return coaches_info
