import requests
import json

from collections import defaultdict
from datetime import datetime


class Client:
    __base_address = 'https://booking.uz.gov.ua/uk/'
    __train_search_url = 'train_search/'

    def __init__(self):
        pass

    def __build_payload_for_search(self, station1, station2, date):
        payload = {}
        payload['date'] = date
        payload['from'] = station1['id']
        payload['to'] = station2['id']
        payload['time'] = '00:00'
        return payload


    def __build_payload_for_coaches_info(self, train, coach_type):
        payload = {}
        payload['from'] = train['from']['code']
        payload['to'] = train['to']['code']
        payload['train'] = train['num']
        payload['date'] = train['from']['srcDate']
        payload['wagon_type_id'] = coach_type
        return payload
    
    
    def __build_payload_for_coach_info(self, train, coach_info_json):
        print(coach_info_json)
        payload = {}
        payload['from'] = train['from']['code']
        payload['to'] = train['to']['code']
        payload['train'] = train['num']
        payload['date'] = train['from']['srcDate']
        payload['wagon_num'] = coach_info_json['num']
        payload['wagon_class'] = coach_info_json['class']
        payload['wagon_type'] = coach_info_json['type']
        return payload


    def find_stations(self, name):
        r = requests.get(self.__base_address + 'train_search/station/?term=' + name)
        print(r.url)
        return r.json()


    def find_trains(self, station1, station2, date):
        payload = self.__build_payload_for_search(station1, station2, date)
        r = requests.post(self.__base_address + 'train_search/', data=payload)
        return r.json()['data']['list']


    def coaches_info_for_train(self, train):
        coaches_info = defaultdict(list) 

        for coach_info in train['types']:
            payload = self.__build_payload_for_coaches_info(train, coach_info['id'])
            response_data = requests.post(self.__base_address + 'train_wagons/', data=payload).json()

            for coach_info_json in response_data['data']['wagons']:
                payload = self.__build_payload_for_coach_info(train, coach_info_json)
                response_data = requests.post(self.__base_address + 'train_wagon/', data=payload).json()
                print(response_data)
                coach_info_json['places'] = response_data['data']['places']
                coaches_info[coach_info_json['type']].append(coach_info_json)

        return coaches_info
