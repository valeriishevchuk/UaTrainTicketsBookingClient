from train_booking.client import Client

if __name__ == '__main__':
    c = Client()
    station1 = { 'id': '2200001'}
    station2 = { 'id': '2210700'}
    date = '04.22.2015'

    print(c.find_trains(station1, station2, date))
