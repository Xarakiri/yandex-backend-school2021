import os

import models
import psycopg2.extras
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy_utils import create_database, drop_database
from sqlalchemy_utils.functions.database import database_exists

from ..main import app, get_db

# Загружаем переменные среды
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

SQLALCHEMY_DATABASE_URL = "postgresql://{}:{}@localhost:5432/{}".format(
    os.environ.get('USERNAME'),
    os.environ.get('DBPW'),
    os.environ.get('TEST_DB_NAME'),
)


@pytest.fixture(scope='function')
def postgres():
    if database_exists(SQLALCHEMY_DATABASE_URL):
        drop_database(SQLALCHEMY_DATABASE_URL)
    create_database(SQLALCHEMY_DATABASE_URL)

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine)

    db: Session = TestingSessionLocal()
    db.execute('create type timerange as range (subtype = time);')
    db.commit()

    conn = engine.raw_connection()
    cur = conn.cursor()
    psycopg2.extras.register_range(
        'timerange', models.TimeRange, cur, globally=True)
    cur.close()
    conn.close()

    models.Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    drop_database(SQLALCHEMY_DATABASE_URL)


@pytest.fixture
def client(postgres):
    with TestClient(app) as tc:
        yield tc
