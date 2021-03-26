import datetime
import json

from .test_base import client, postgres
from .utils import generate_courier, generate_order


def test_order_complete(client):
    # Создаем курьера
    response = client.post(
        '/couriers',
        data=json.dumps({
            'data': [generate_courier(courier_id=1,
                                      regions=[4, 12, 7],
                                      working_hours=['12:00-20:00'])]
        }))
    assert response.status_code == 201

    # Создаем заказ
    response = client.post(
        '/orders',
        data=json.dumps({
            'data': [generate_order(order_id=4,
                                    region=7,
                                    delivery_hours=['11:00-13:00']),
                     generate_order(order_id=5,
                                    region=7,
                                    delivery_hours=['21:00-21:30']),
                     ]
        }))
    assert response.status_code == 201

    response = client.post('/orders/assign',
                           data=json.dumps({'courier_id': 1}))

    assert response.status_code == 200
    assert response.json()['orders'] == [{'id': 4}]

    response = client.post(
        '/orders/complete',
        data=json.dumps({
            'courier_id': 1,
            'order_id': 4,
            'complete_time': datetime.datetime.now().isoformat('T')+'Z'
        }))

    assert response.status_code == 200
    assert response.json() == {'order_id': 4}
