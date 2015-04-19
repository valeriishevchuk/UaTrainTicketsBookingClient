from train_booking.client import Client

if __name__ == '__main__':
    c = Client()
    station1 = { 'id': '2200001'}
    station2 = { 'id': '2218000'}
    date = '05.20.2015'

    trains = c.find_trains(station1, station2, date)
    print(trains[0])
    print(c.coaches_info_for_train(trains[0]))

