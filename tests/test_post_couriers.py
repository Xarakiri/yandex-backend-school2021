import json

import pytest

from .test_base import client, postgres
from .utils import generate_courier


@pytest.mark.parametrize(
    'courier',
    [generate_courier(courier_id=i) for i in range(1, 10)]
)
def test_post_couriers(client, courier):
    response = client.post('/couriers', data=json.dumps({'data': [courier]}))

    assert response.status_code == 201


@pytest.mark.parametrize(
    'courier',
    [
        generate_courier(courier_id=-1),
        generate_courier(courier_type='ski'),
        generate_courier(regions=[-1, 'a']),
        generate_courier(working_hours=['123123'])
    ]
)
def test_post_couriers_negative(client, courier):
    response = client.post('/couriers', data=json.dumps({'data': [courier]}))

    assert response.status_code == 400
