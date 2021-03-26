import psycopg2.extras
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy import types as sqltypes
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from database import Base, engine


class TimeRange(psycopg2.extras.Range):
    pass


conn = engine.raw_connection()
cur = conn.cursor()
psycopg2.extras.register_range('timerange', TimeRange, cur, globally=True)
cur.close()
conn.close()


class TIMERANGE(postgresql.ranges.RangeOperators, sqltypes.UserDefinedType):
    def get_col_spec(self, **kw):
        return 'timerange'


postgresql.base.ischema_names['timerange'] = TIMERANGE


class Courier(Base):
    __tablename__ = 'couriers'

    courier_id = Column(Integer, primary_key=True)
    courier_type = Column(String(20))
    orders_weight = Column(Float(2), default=0)
    regions = relationship("Region", back_populates="region_owner")
    working_hours = relationship("WorkingHours", back_populates="wh_owner")


class Region(Base):
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True)
    region_id = Column(Integer)
    courier_id = Column(Integer, ForeignKey('couriers.courier_id'))

    region_owner = relationship("Courier", back_populates="regions")


class WorkingHours(Base):
    __tablename__ = 'working_hours'

    id = Column(Integer, primary_key=True)
    courier_id = Column(Integer, ForeignKey('couriers.courier_id'))
    working_hours = Column(TIMERANGE())

    wh_owner = relationship("Courier", back_populates="working_hours")


class Order(Base):
    __tablename__ = 'orders'

    order_id = Column(Integer, primary_key=True)
    weight = Column(Float)
    region = Column(Integer)
    taken = Column(Boolean, default=False)
    delivery_hours = relationship("DeliveryHours", back_populates="dh_owner")


class DeliveryHours(Base):
    __tablename__ = 'delivery_hours'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.order_id'))
    delivery_hours = Column(TIMERANGE())

    dh_owner = relationship("Order", back_populates="delivery_hours")


class CouriersOrders(Base):
    __tablename__ = 'couriers_orders'

    id = Column(Integer, primary_key=True)

    order_id = Column(Integer)
    courier_id = Column(Integer)
    assign_time = Column(String)
    complete_time = Column(String, nullable=True)
    delivery_time = Column(Integer, default=0)
