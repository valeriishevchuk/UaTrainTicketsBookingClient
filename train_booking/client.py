import requests
import json


class Client:
    __base_address = 'http://www.booking.uz.gov.ua/'

    def find_stations(self, name):
        station = 'purchase/station/'
        r = requests.post(self.__base_address + station + name)
        data = json.loads(r.text)
        return data['value'] if data['error'] != 'None' else None
