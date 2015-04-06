from train_booking.client import Client

if __name__ == '__main__':
    c = Client()
    station1 = { 'id': '2200001'}
    station2 = { 'id': '2218165'}
    date = '15.04.2015'

    print(c.find_tickets(station1, station2, date))
