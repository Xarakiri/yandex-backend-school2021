from random import choice, randint
from typing import Any, Dict, List, Optional

import pytest

MAX_INT = 100000


def generate_courier(
    courier_id: Optional[int] = None,
    courier_type: Optional[str] = None,
    regions: Optional[List[int]] = None,
    working_hours: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Создает и возвращает курьера, автоматически генерируя данные для не
    указанных полей.
    """
    if courier_id is None:
        courier_id = randint(1, MAX_INT)

    if courier_type is None:
        courier_type = choice(['foot', 'bike', 'car'])

    if regions is None:
        regions = [randint(1, 20) for i in range(4)]

    if working_hours is None:
        start_time = randint(10, 19)
        stop_time = start_time + 4
        working_hours = [f'{start_time}:00-{stop_time}:00']

    return {
        'courier_id': courier_id,
        'courier_type': courier_type,
        'regions': regions,
        'working_hours': working_hours,
    }


def generate_order(
    order_id: Optional[int] = None,
    weight: Optional[float] = None,
    region: Optional[int] = None,
    delivery_hours: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Создает и возвращает order, автоматически генерируя данные для не
    указанных полей.
    """
    if order_id is None:
        order_id = randint(1, MAX_INT)

    if weight is None:
        weight = randint(1, 10) - 0.5

    if region is None:
        region = randint(1, 20)

    if delivery_hours is None:
        start_time = randint(10, 19)
        stop_time = start_time + 4
        delivery_hours = [f'{start_time}:00-{stop_time}:00']

    return {
        'order_id': order_id,
        'weight': weight,
        'region': region,
        'delivery_hours': delivery_hours,
    }
