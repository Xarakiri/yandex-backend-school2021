import re
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field, conlist, root_validator, validator


def check_time(time: str) -> str:
    pattern = re.compile(
        r'(?:[01]\d|2[0-3]):(?:[0-5]\d)-(?:[01]\d|2[0-3]):(?:[0-5]\d)')
    if not re.match(pattern, time):
        raise ValueError('Working hours has invalid type.')
    return time


class CourierTypeEnum(str, Enum):
    foot = 'foot'
    bike = 'bike'
    car = 'car'

    class Config:
        orm_mode = True


class BaseRegion(BaseModel):
    id: int = Field(..., gt=0)

    class Config:
        orm_mode = True


class BaseWorkingHours(BaseModel):
    courier_id: int = Field(..., gt=0)

    class Config:
        orm_mode = True


class Region(BaseRegion):
    courier_id: int = Field(..., gt=0)

    class Config:
        orm_mode = True


class WorkingHours(BaseWorkingHours):
    working_hours: List[str]

    # validators
    _check_working_hours = validator(
        'working_hours', allow_reuse=True, each_item=True)(check_time)

    class Config:
        orm_mode = True


class CourierBase(BaseModel):
    courier_id: int = Field(..., gt=0)
    courier_type: CourierTypeEnum = Field(...)
    regions: conlist(int, min_items=1)
    working_hours: conlist(str, min_items=1)

    # validators
    _check_working_hours = validator(
        'working_hours', allow_reuse=True, each_item=True)(check_time)

    @validator('regions', each_item=True)
    def check_regions(cls, v):
        assert v > 0, 'Region must be greater than 0.'
        return v

    class Config:
        orm_mode = True


class CourierRating(BaseModel):
    courier_id: int
    courier_type: str
    regions: List[Any]
    working_hours: List[Any]
    rating: float = 0
    earnings: int = 0

    @validator('regions')
    def validate_regions(cls, v):
        answer = []
        for i in v:
            if hasattr(i, 'region_id'):
                answer.append(i.region_id)
        return answer

    @validator('working_hours')
    def validate_wh(cls, v):
        answer = []
        for i in v:
            if hasattr(i, 'working_hours'):
                answer.append(
                    '-'.join(re.findall(r'(?:[01]\d|2[0-3]):(?:[0-5]\d)', str(i.working_hours))))
        return answer


class CourierPatchInput(BaseModel):
    courier_type: Optional[CourierTypeEnum]
    regions: Optional[conlist(int, min_items=1)]
    working_hours: Optional[conlist(str, min_items=1)]

    # validators
    _check_working_hours = validator(
        'working_hours', allow_reuse=True, each_item=True)(check_time)

    @root_validator
    def any_of(cls, v):
        if not any(v.values()):
            raise ValueError('One if field is required.')
        return v

    @validator('regions', each_item=True)
    def check_regions(cls, v):
        assert v > 0, 'Region must be greater than 0.'
        return v


class CourierPatch(BaseModel):
    courier_id: int
    courier_type: str
    regions: List[Any]
    working_hours: List[Any]

    @validator('regions')
    def validate_regions(cls, v):
        answer = []
        for i in v:
            if hasattr(i, 'region_id'):
                answer.append(i.region_id)
        return answer

    @validator('working_hours')
    def validate_wh(cls, v):
        answer = []
        for i in v:
            if hasattr(i, 'working_hours'):
                answer.append(
                    '-'.join(re.findall(r'(?:[01]\d|2[0-3]):(?:[0-5]\d)', str(i.working_hours))))
        return answer

    class Config:
        orm_mode = True


class CouriersPostRequest(BaseModel):
    data: List[CourierBase]

    class Config:
        orm_mode = True


class CourierId(BaseModel):
    id: int = Field(..., gt=0)

    class Config:
        orm_mode = True


class CouriersIds(BaseModel):
    couriers: List[CourierId]

    class Config:
        orm_mode = True


class CouriersBadRequest(BaseModel):
    validation_error: List[CouriersIds]

    class Config:
        orm_mode = True


class OrderBase(BaseModel):
    order_id: int = Field(..., gt=0)
    weight: float
    region: int = Field(..., gt=0)
    delivery_hours: conlist(str, min_items=1)

    # validators
    _check_working_hours = validator(
        'delivery_hours', allow_reuse=True, each_item=True)(check_time)

    @validator('weight')
    def check_weight(cls, v):
        if v < 0.01 or v > 50:
            raise ValueError('Weight not valid.')
        return round(v, 2)

    class Config:
        orm_mode = True


class OrderId(BaseModel):
    id: int = Field(..., gt=0)

    class Config:
        orm_mode = True


class OrdersIds(BaseModel):
    orders: List[CourierId]

    class Config:
        orm_mode = True


class OrdersAssign(BaseModel):
    orders: List[CourierId]
    assign_time: str = ''

    class Config:
        orm_mode = True


class OrdersPostRequest(BaseModel):
    data: List[OrderBase]

    class Config:
        orm_mode = True


class OrderAssign(BaseModel):
    courier_id: int = Field(..., gt=0)


class OrdersComplete(BaseModel):
    courier_id: int = Field(..., gt=0)
    order_id: int = Field(..., gt=0)
    complete_time: str = Field(...)

    @validator('complete_time')
    def check_time(cls, v):
        pattern = re.compile(
            r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)Z$')
        try:
            if re.match(pattern, v):
                return v
        except:
            raise ValueError('Invalid time format.')


class OrderCompleteAnswer(BaseModel):
    order_id: int = Field(..., gt=0)
