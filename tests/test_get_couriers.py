import json

import pytest

from .test_base import client, postgres
from .utils import generate_courier


@pytest.mark.parametrize(
    'courier',
    [generate_courier(courier_id=i) for i in range(1, 3)]
)
def test_get_couriers(client, courier):
    response = client.post('/couriers', data=json.dumps({'data': [courier]}))

    assert response.status_code == 201

    response = client.get(f'/couriers/{courier["courier_id"]}')

    assert response.status_code == 200
    assert response.json() == courier
