from geopy.distance import vincenty

from casap.utilities.utils import get_address_map_google


def print_test():
    address = \
        'Mundy Park Hillcrest Parking Lot, Hillcrest Street, Coquitlam, BC, Canada'
    address_list = [
        ['Mundy Park Off Leash Dog Park, Mariner Way, Coquitlam, BC, Canada'
            , 3],
        ['Mundy Lake, Coquitlam, BC, Canada', 1],
        ['Lost Lake, Coquitlam, BC, Canada', 3],
        ['Mundy Park Softball Fields, Coquitlam, BC, Canada', 1],
        ['Starbucks, 2662 Austin Avenue, Coquitlam, BC, Canada', 3],
        ['Coquitlam Alliance Church, Spuraway Avenue, Coquitlam, BC, Canada'
            , 3],
        ['Riverview Forest, Coquitlam, BC, Canada', 3],
        ['Spani Outdoor Pool, Coquitlam, BC, Canada', 1],
    ]

    for i in range(10):
        add = get_address_map_google(address)
        if add is None:
            add = get_address_map_google(address)
        else:
            break
    add_lat = add['lat']
    add_lng = add['lng']
    print('Missing Location: {}'.format(address))
    for x in address_list:
        for i in range(10):
            x_add = get_address_map_google(x[0])
            if x_add is None:
                x_add = get_address_map_google(x[0])
            else:
                break
        x_lat = x_add['lat']
        x_lng = x_add['lng']
        vin = vincenty((x_lat, x_lng), (add_lat, add_lng)).kilometers
        if vin <= x[1]:
            print('{}  |  {}  |  {}  |  {}'.format(x[0], x[1], vin, 'yes'))
        else:
            print('{}  |  {}  |  {}  |  {}'.format(x[0], x[1], vin, 'yes'))
