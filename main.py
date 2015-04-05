from train_booking.client import Client

if __name__ == '__main__':
    c = Client()
    print(c.find_stations('dffdd'))
