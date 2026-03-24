import logging

from app import engine
from database.auth.auth_schema import Auth, Data

# set logger
logging.basicConfig(level=logging.INFO)

with engine.begin() as conn:
    # migration
    Data.__table__.create(bind=conn, checkfirst=True)
    Auth.__table__.create(bind=conn, checkfirst=True)
