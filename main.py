import re
from typing import Dict, Tuple

from fastapi import Depends, FastAPI, Path, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from starlette.responses import PlainTextResponse

import crud
import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ValidationErrorHandler:
    @classmethod
    def http400(cls, exc, **kwargs):
        return PlainTextResponse(status_code=status.HTTP_400_BAD_REQUEST)

    @classmethod
    def invalid_post(cls, exc, who: str, who_id: str, db: SessionLocal = SessionLocal()):
        invalid_data = {who: []}
        for i in exc.body['data']:
            invalid_data[who].append({'id': i[who_id]})
        return PlainTextResponse(
            content=str({'validation_error': invalid_data}),
            status_code=status.HTTP_400_BAD_REQUEST
        )


handlers = {
    'couriers': ValidationErrorHandler.invalid_post,
    'couriers_patch': ValidationErrorHandler.http400,
    'orders': ValidationErrorHandler.invalid_post,
    'orders/assign': ValidationErrorHandler.http400,
    'orders/complete': ValidationErrorHandler.http400
}


def parse_url(request: str) -> Tuple[str, Dict[str, str]]:
    path = request.url.path.strip('/')
    answer = {'who': 'couriers', 'who_id': 'courier_id'}
    if re.match(r'couriers/\d+', path):
        path = 'couriers_patch'
        return path, answer
    if path == 'orders':
        answer['who'] = 'orders'
        answer['who_id'] = 'order_id'
        return path, answer
    if path in ('couriers', 'orders/assign', 'orders/complete'):
        return path, answer
    raise Exception(f'URL NOT VALID {path}')


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request, exc):
    path, kwargs = parse_url(request)
    return handlers[path](exc, **kwargs)


def any_courier_in_db(db: Session, couriers: schemas.CouriersPostRequest):
    for item in couriers.data:
        courier = crud.get_courier_by_id(db=db, id=item.courier_id)
        if courier:
            return True
    return False


def any_order_in_db(db: Session, orders: schemas.OrdersPostRequest):
    for item in orders.data:
        order1 = crud.get_order_by_id(db=db, id=item.order_id)
        order2 = db.query(models.CouriersOrders).filter(
            models.CouriersOrders.order_id == item.order_id
        ).first()
        if order1 or order2:
            return True
    return False


@app.post(
    "/couriers",
    response_model=schemas.CouriersIds,
    status_code=status.HTTP_201_CREATED,
    response_description='Import couriers')
def add_couriers(
        couriers: schemas.CouriersPostRequest,
        db: Session = Depends(get_db)):

    # Если какой-нибудь из курьеров уже есть в бд,
    # то возвращаем их id
    if any_courier_in_db(db=db, couriers=couriers):
        invalid_data = {'couriers': []}
        for i in couriers.data:
            invalid_data['couriers'].append({'id': i.courier_id})
        return PlainTextResponse(content=str({'validation_error': invalid_data}), status_code=status.HTTP_400_BAD_REQUEST)

    answer = crud.add_couriers(
        db=db,
        couriers=couriers
    )

    return answer


@app.patch('/couriers/{courier_id}', response_model=schemas.CourierPatch)
def patch_courier(data: schemas.CourierPatchInput,
                  courier_id: int = Path(..., gt=0), db=Depends(get_db)):
    c = crud.get_courier_by_id(db=db, id=courier_id)
    if not c:
        return PlainTextResponse(status_code=status.HTTP_400_BAD_REQUEST)
    return crud.patch_courier(db=db, courier_id=courier_id, input=data)


@app.post(
    '/orders',
    response_model=schemas.OrdersIds,
    status_code=status.HTTP_201_CREATED,
    response_description='Import orders')
def post_orders(orders: schemas.OrdersPostRequest,
                db: Session = Depends(get_db)):
    if any_order_in_db(db=db, orders=orders):
        invalid_data = {'orders': []}
        for i in orders.data:
            invalid_data['orders'].append({'id': i.order_id})
        return PlainTextResponse(content=str({'validation_error': invalid_data}), status_code=status.HTTP_400_BAD_REQUEST)

    answer = crud.add_orders(
        db=db,
        orders=orders
    )

    return answer


@app.get('/couriers/{courier_id}', response_model=schemas.CourierRating, response_model_exclude_unset=True)
def get_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = crud.get_courier_by_id(db=db, id=courier_id)
    if courier:
        return crud.get_courier(db=db, courier_id=courier_id)
    return PlainTextResponse(status_code=status.HTTP_400_BAD_REQUEST)


@app.post('/orders/assign', response_model=schemas.OrdersAssign, response_model_exclude_unset=True)
def orders_assign(assign: schemas.OrderAssign,
                  db: Session = Depends(get_db)):
    # Если передан идентификатор несуществующего курьера
    courier = crud.get_courier_by_id(db=db, id=assign.courier_id)
    if not courier:
        return PlainTextResponse(status_code=status.HTTP_400_BAD_REQUEST)
    return crud.get_max_assigns_for_courier(db=db, courier_id=assign.courier_id)


@app.post('/orders/complete', response_model=schemas.OrderCompleteAnswer)
def orders_complete(complete: schemas.OrdersComplete, db: Session = Depends(get_db)):
    # Проверка есть ли у курьера незавершенный заказ с таким номером
    order = db.query(models.CouriersOrders).filter(
        models.CouriersOrders.order_id == complete.order_id,
        models.CouriersOrders.courier_id == complete.courier_id,
        models.CouriersOrders.complete_time == None).first()

    # Если такого заказа нет, возвращаем 400
    if not order:
        return PlainTextResponse(status_code=status.HTTP_400_BAD_REQUEST)

    return crud.orders_complete(db=db, complete=complete)
