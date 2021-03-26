import json
from random import randint

import pytest
from fastapi.testclient import TestClient

from .test_base import client, postgres
from .utils import generate_courier


@pytest.mark.parametrize(
    'regions',
    [
        [randint(1, 20) for i in range(4)] for j in range(3)
    ]
)
def test_change_courier_regions(client: TestClient, regions):
    response = client.post(
        '/couriers', data=json.dumps({'data': [generate_courier(courier_id=1)]}))

    response = client.patch(
        '/couriers/1', data=json.dumps({'regions': regions}))

    assert response.json()['regions'] == regions


@pytest.mark.parametrize(
    'type',
    [
        'foot',
        'car',
        'bike',
    ]
)
def test_change_courier_type(client: TestClient, type):
    response = client.post(
        '/couriers', data=json.dumps({'data': [generate_courier(courier_id=2)]}))

    response = client.patch(
        '/couriers/2', data=json.dumps({'courier_type': type}))

    assert response.json()['courier_type'] == type


@pytest.mark.parametrize(
    'wh',
    [
        generate_courier()['working_hours'] for i in range(3)
    ]
)
def test_change_courier_working_hours(client: TestClient, wh):
    response = client.post(
        '/couriers', data=json.dumps({'data': [generate_courier(courier_id=1)]}))

    response = client.patch(
        '/couriers/1', data=json.dumps({'working_hours': wh}))

    assert response.json()['working_hours'] == wh
