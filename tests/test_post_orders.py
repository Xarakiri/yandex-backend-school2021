import json

import pytest

from .test_base import client, postgres
from .utils import generate_order


@pytest.mark.parametrize(
    'order',
    [generate_order(order_id=i) for i in range(1, 10)]
)
def test_post_orders(client, order):
    response = client.post('/orders', data=json.dumps({'data': [order]}))

    assert response.status_code == 201


@pytest.mark.parametrize(
    'order',
    [
        generate_order(order_id=-1),
        generate_order(weight=-0.12),
        generate_order(region=0),
        generate_order(delivery_hours=['12:00-25:00'])
    ]
)
def test_post_orders_negative(client, order):
    response = client.post('/orders', data=json.dumps({'data': [order]}))

    assert response.status_code == 400

