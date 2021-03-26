import datetime
import json
from random import randint

from locust import HttpUser, TaskSet, task
from tests.utils import generate_courier, generate_order

j, i = 0, 0


def post_couriers(l):
    global i
    i += 1
    l.client.post(
        '/couriers',
        json.dumps({
            'data': [generate_courier(courier_id=i)]
        }))


def post_orders(l):
    global j
    j += 1
    l.client.post(
        '/orders',
        json.dumps({
            'data': [generate_order(order_id=j)]
        }))


def patch_courier(l):
    global i
    l.client.patch(
        f'/couriers/{randint(1, i)}', data=json.dumps({'regions': [randint(1, 20) for i in range(4)]}))


def post_orders_assign(l):
    global i
    l.client.post('/orders/assign', data=json.dumps({'courier_id': i}))


def post_orders_complete(l):
    global i
    global j
    l.client.post('/orders/complete', data=json.dumps({
        'courier_id': randint(1, i),
        'order_id': randint(1, j),
        'complete_time': datetime.datetime.now().isoformat('T')+'Z',
    }))


def get_couriers(l):
    global i
    l.client.get(f'/couriers/{randint(1, i)}')


class UserBehavior(TaskSet):
    @task
    def workflow(self):
        post_couriers(self)
        post_orders(self)
        patch_courier(self)
        post_orders_assign(self)
        post_orders_complete(self)
        get_couriers(self)


class WebsiteUser(HttpUser):
    tasks = [UserBehavior]
    min_wait = 5000
    max_wait = 9000
