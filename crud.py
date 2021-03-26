import datetime
import operator
from collections import defaultdict
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
import schemas
from models import TimeRange

carrying_capacity = {
    "foot": 10,
    "bike": 15,
    "car": 50,
}

coefficients = {
    'foot': 2,
    'bike': 3,
    'car': 9,
}


def get_order_by_id(db: Session, id: int):
    return db.query(models.Order).filter(models.Order.order_id == id).first()


def get_couriers(db: Session):
    return db.query(models.Courier).all()


def get_courier_by_id(db: Session, id: int) -> models.Courier:
    return db.query(models.Courier).filter(models.Courier.courier_id == id).first()


def _add_regions_for_courier(db: Session, courier_id: int, regions: List[int]):
    for r in regions:
        region = models.Region(region_id=r, courier_id=courier_id)
        db.add(region)
        db.commit()
        db.refresh(region)


def get_actual_courier_weight(db: Session, courier_id: int):
    # Заказы курьера
    orders = db.query(models.CouriersOrders, models.Order).filter(
        models.CouriersOrders.courier_id == courier_id,
        models.Order.order_id == models.CouriersOrders.order_id
    ).all()
    if orders:
        return round(sum([i[1].weight for i in orders]), 2)
    return 0


def check_orders_after_patch(
        db: Session,
        courier_id: int,
        type: bool,
        regions: bool,
        working_hours: bool):

    # Курьер
    courier = get_courier_by_id(db=db, id=courier_id)

    # Заказы курьера
    orders = db.query(models.CouriersOrders).filter(
        models.CouriersOrders.courier_id == courier_id,
        models.CouriersOrders.complete_time == None
    ).all()

    # Если заказы есть
    if orders:
        # Проверка по регионам
        if regions:
            courier_regions = [i.region_id for i in db.query(models.Region).filter(
                models.Region.courier_id == courier_id
            ).all()]

            for order in orders:
                order_region = db.query(models.Order).filter(
                    models.Order.order_id == order.order_id
                ).first()

                # Если заказ не входит в регионы курьера
                if order_region.region not in courier_regions:
                    db.delete(order)
                    order_region.taken = False
                    db.flush()

            actual_weight = get_actual_courier_weight(
                db=db, courier_id=courier_id)
            courier.orders_weight = actual_weight
            db.commit()

        # Проверка по графику работы
        if working_hours:
            # Обновляем заказы курьера
            orders = db.query(models.CouriersOrders).filter(
                models.CouriersOrders.courier_id == courier_id,
                models.CouriersOrders.complete_time == None
            ).all()

            courier_wh = db.query(models.WorkingHours).filter(
                models.WorkingHours.courier_id == courier_id
            ).all()

            for order in orders:
                # Уже удаленные заказы
                deleted_orders = set()

                # Промежутки, в которые клиенту удобно принять заказ
                order_dh = db.query(models.DeliveryHours).filter(
                    models.DeliveryHours.order_id == order.order_id
                ).all()

                for wh in courier_wh:
                    for dh in order_dh:
                        if order.order_id not in deleted_orders and not (dh.delivery_hours.lower < wh.working_hours.upper and dh.delivery_hours.upper > wh.working_hours.lower):
                            db.delete(order)
                            db.query(models.Order).filter(
                                models.Order.order_id == order.order_id
                            ).update(
                                {'taken': False}
                            )
                            deleted_orders.add(order.order_id)
                            db.flush()

            actual_weight = get_actual_courier_weight(
                db=db, courier_id=courier_id)
            courier.orders_weight = actual_weight
            db.commit()

        if type:
            # Обновляем заказы курьера
            orders = db.query(models.CouriersOrders, models.Order).filter(
                models.CouriersOrders.courier_id == courier_id,
                models.CouriersOrders.complete_time == None,
                models.Order.order_id == models.CouriersOrders.order_id
            ).order_by(models.Order.weight.asc()).all()

            max_capacity = carrying_capacity[courier.courier_type]

            # Если вес заказов, больше чем курьер может унести
            while len(orders) > 0 and courier.orders_weight > max_capacity:
                order = orders.pop()
                courier.orders_weight = models.Courier.orders_weight - \
                    order[1].weight
                db.flush()

                # Удаляем запись из таблицы couriers_orders
                db.delete(order[0])

                # Обновляем столбец, в таблице orders
                db.query(models.Order).filter(
                    models.Order.order_id == order[1].order_id
                ).update(
                    {'taken': False}
                )
            db.commit()


def patch_courier(db: Session, courier_id: int, input: schemas.CourierPatchInput):
    # Словарь, который хранит, что изменилось при патче
    changed = {
        'type': False,
        'regions': False,
        'working_hours': False,
    }

    if input.courier_type:
        print('ok')
        db.query(models.Courier).filter(models.Courier.courier_id == courier_id).update(
            {models.Courier.courier_type: input.courier_type}, synchronize_session=False)
        changed['type'] = True

    if input.regions:
        db.query(models.Region).filter(models.Region.courier_id ==
                                       courier_id).delete(synchronize_session=False)
        _add_regions_for_courier(
            db=db, courier_id=courier_id, regions=input.regions)
        changed['regions'] = True

    if input.working_hours:
        db.query(models.WorkingHours).filter(
            models.WorkingHours.courier_id == courier_id).delete(synchronize_session=False)
        _add_working_hours_for_courier(
            db=db, courier_id=courier_id, working_hours=input.working_hours)
        changed['working_hours'] = True

    db.commit()

    check_orders_after_patch(db=db, courier_id=courier_id, **changed)
    return get_courier_by_id(db=db, id=courier_id)


def _add_courier(db: Session, courier: models.Courier):
    db.add(courier)
    db.commit()
    db.refresh(courier)


def _add_order(db: Session, order: models.Order):
    db.add(order)
    db.commit()
    db.refresh(order)


def _add_delivery_hours_for_order(db: Session, order_id: int, delivery_hours: List[str]):
    for dh in delivery_hours:
        start, _, stop = dh.rpartition('-')
        dh = models.DeliveryHours(
            order_id=order_id,
            delivery_hours=TimeRange(
                datetime.time(*list(map(int, start.split(':')))),
                datetime.time(*list(map(int, stop.split(':')))),
                '[]')
        )
        db.add(dh)
        db.commit()
        db.refresh(dh)


def _add_working_hours_for_courier(db: Session, courier_id: int, working_hours: List[str]):
    for wh in working_hours:
        start, _, stop = wh.rpartition('-')
        wh = models.WorkingHours(
            courier_id=courier_id,
            working_hours=TimeRange(
                datetime.time(*list(map(int, start.split(':')))),
                datetime.time(*list(map(int, stop.split(':')))),
                '[]')
        )
        db.add(wh)
        db.commit()
        db.refresh(wh)


def add_orders(db: Session, orders: schemas.OrdersPostRequest):
    answer = defaultdict(list)
    for i in orders.data:
        id = schemas.OrderId(id=i.order_id)

        order = models.Order(
            order_id=i.order_id,
            weight=i.weight,
            region=i.region
        )

        _add_order(db, order)
        _add_delivery_hours_for_order(db, i.order_id, i.delivery_hours)

        answer['orders'].append(id)
    return answer


def add_couriers(db: Session, couriers: schemas.CouriersPostRequest):
    answer = defaultdict(list)
    for i in couriers.data:
        id = schemas.CourierId(id=i.courier_id)

        courier = models.Courier(
            courier_id=i.courier_id,
            courier_type=i.courier_type,
        )
        _add_courier(db, courier)
        _add_regions_for_courier(db, i.courier_id, i.regions)
        _add_working_hours_for_courier(db, i.courier_id, i.working_hours)

        answer['couriers'].append(id)
    return answer


def get_max_assigns_for_courier(db: Session, courier_id: int):
    # Ответ
    answer = {'orders': []}

    # Время назначения заказа
    assign_time = datetime.datetime.now().isoformat('T') + 'Z'

    # Сколько курьер может унести
    courier = get_courier_by_id(db, courier_id)
    capacity = carrying_capacity[courier.courier_type] - courier.orders_weight
    orders_weight = courier.orders_weight

    # Регионы курьера
    regions = [i.region_id for i in db.query(models.Region).filter(
        models.Region.courier_id == courier_id).all()]

    # Список, времени работы курьера
    working_hours = db.query(models.WorkingHours).filter(
        models.WorkingHours.courier_id == courier_id).all()

    # Выбираем orders, с подходящим регионом и весом не больше максимальноного
    orders = db.query(models.Order).filter(models.Order.region.in_(regions), models.Order.weight <=
                                           capacity, models.Order.taken == False).order_by(models.Order.weight.asc())

    # Список orders которые назначим курьеру
    to_assign = []
    assigned_orders = set()

    # Находим заказы, подходящие по времени
    for order in orders:
        # Промежутки, в которые клиенту удобно принять заказ
        delivery_hours = db.query(models.DeliveryHours).filter(
            models.DeliveryHours.order_id == order.order_id).all()

        if orders_weight + order.weight > capacity:
            break

        for dh in delivery_hours:
            for wh in working_hours:
                if order.order_id not in assigned_orders and dh.delivery_hours.lower < wh.working_hours.upper and dh.delivery_hours.upper > wh.working_hours.lower:
                    assigned_orders.add(order.order_id)

                    # Указываем в таблице order, что заказ взят
                    db.query(models.Order).filter(models.Order.order_id ==
                                                  order.order_id).update({models.Order.taken: True})
                    db.commit()

                    # Добавляем пару курьер-заказ в таблицу couriers_orders
                    courier_order = models.CouriersOrders(
                        order_id=order.order_id,
                        courier_id=courier_id,
                        assign_time=assign_time,
                        #id = order.order_id
                    )

                    to_assign.append(courier_order)
                    orders_weight += order.weight

                    answer['orders'].append({'id': order.order_id})

    # Коммитим заказы в бд
    if to_assign:
        db.add_all(to_assign)

    # Обновляем вес курьера
    db.query(models.Courier).filter(models.Courier.courier_id ==
                                    courier_id).update({models.Courier.orders_weight: orders_weight})
    db.commit()

    # Если не удалось найти подходящих заказов, assign_time возвращать не нужно
    if answer['orders']:
        answer['assign_time'] = assign_time

    return answer


def get_delivery_time(db: Session, complete: schemas.OrdersComplete) -> int:
    # Время окончания этого заказа
    this_order_end_time = datetime.datetime.strptime(
        complete.complete_time,
        '%Y-%m-%dT%H:%M:%S.%fZ'
    )

    # Находим все предыдущие заказы курьера
    orders = db.query(models.CouriersOrders).filter(
        models.CouriersOrders.courier_id == complete.courier_id,
        models.CouriersOrders.complete_time != None
    ).all()

    # Время доставки = разница между временем окончания этого заказа
    # и временем окончания предыдущего
    if orders:
        orders_prev = [
            datetime.datetime.strptime(
                i.complete_time, '%Y-%m-%dT%H:%M:%S.%fZ')
            for i in orders
        ]
        orders_prev.sort()
        prev_order_end_time = orders_prev[-1]
    # Если это первый выполненный заказ
    else:
        prev_order = db.query(models.CouriersOrders).filter(
            models.CouriersOrders.order_id == complete.order_id
        ).first()
        prev_order_end_time = datetime.datetime.strptime(
            prev_order.assign_time,
            '%Y-%m-%dT%H:%M:%S.%fZ'
        )
    return (this_order_end_time - prev_order_end_time).seconds


def orders_complete(db: Session, complete: schemas.OrdersComplete):
    # Обновляем таблицу couriers_orders
    db.query(models.CouriersOrders).filter(
        models.CouriersOrders.courier_id == complete.courier_id,
        models.CouriersOrders.order_id == complete.order_id
    ).update(
        {'complete_time': complete.complete_time,
         'delivery_time': get_delivery_time(db, complete)},
        synchronize_session=False
    )

    # Получаем заказ
    order = db.query(models.Order).filter(
        models.Order.order_id == complete.order_id
    ).first()

    # TODO зачем хз
    # Удаляем записи из таблицы delivery_hours
    # db.query(models.DeliveryHours).filter(
    #    models.DeliveryHours.order_id == order.order_id
    # ).delete(synchronize_session=False)

    # Обновляем вес курьера в таблице orders
    courier = db.query(models.Courier).filter(
        models.Courier.courier_id == complete.courier_id
    ).first()

    current_weight = round(courier.orders_weight - order.weight, 2)
    courier.orders_weight = current_weight

    db.commit()

    return schemas.OrderCompleteAnswer(order_id=complete.order_id)


def get_courier(db: Session, courier_id: int):
    courier = get_courier_by_id(db=db, id=courier_id)

    answer = {
        'courier_id': courier.courier_id,
        'courier_type':  courier.courier_type,
        'regions': courier.regions,
        'working_hours': courier.working_hours,
    }

    # Заработок курьера
    N = len(db.query(models.CouriersOrders).filter(
        models.CouriersOrders.courier_id == courier_id,
        models.CouriersOrders.complete_time != None
    ).all())
    sum = N * 500 * coefficients[courier.courier_type]

    # Среднее время доставки по регионам
    regions = [i.region_id for i in courier.regions]
    avg_time = db.query(
        models.Order.region,
        func.avg(models.CouriersOrders.delivery_time)
    ).filter(
        models.Order.region.in_(regions)
    ).join(
        models.CouriersOrders,
        models.CouriersOrders.order_id == models.Order.order_id
    ).group_by(
        models.Order.region
    ).all()

    completed_orders = len(db.query(models.CouriersOrders).filter(
        models.CouriersOrders.courier_id == courier_id,
        models.CouriersOrders.delivery_time != 0
    ).all())

    # Если есть выполненные заказы, то добавляем в ответ
    # rating и earnings
    if avg_time and completed_orders > 0:
        t = float(min(avg_time, key=operator.itemgetter(1))[1])
        rating = (60*60 - min(t, 60*60))/(60*60) * 5
        answer['rating'] = round(rating, 2)
        answer['earnings'] = sum

    return answer
