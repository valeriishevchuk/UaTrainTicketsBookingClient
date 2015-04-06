import requests
import json
import execjs
import re


class Client:
    __base_address = 'http://booking.uz.gov.ua/'
    __purchase_url = 'purchase/'

    def __parse_cookie(self, headers_str):
        for cookie in headers_str.split(';'):
            if cookie.startswith('_gv_sessid'):
                self.__cookie_value = cookie + ';'


    def __parse_token(self, html_str):
        p = re.compile('\\$\\$_=.*~\\[\\];.*\"\"\\)\\(\\)\\)\\(\\);')
        m = p.search(html_str)
        
        if not m:
            raise "Can't find obfuscated tocken data."
        
        obfuscated = m.group()
        interceptor = "var token; "

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


    def find_stations(self, name):
        station_url = 'station/'
        full_url = self.__base_address + self.__purchase_url + station_url + name
        r = requests.post(full_url)
        data = json.loads(r.text)
        return data['value'] if data['error'] != 'None' else None


    def find_tickets(self, station1, station2, date):
        search_url = 'search/'
        full_url = self.__base_address + self.__purchase_url + search_url
        payload = self.__build_payload_for_search(station1, station2, date)
        r = requests.post(full_url, data=payload, headers=self.__build_headers())
        return json.loads(r.text)
