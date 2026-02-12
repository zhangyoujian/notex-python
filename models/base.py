import uuid
from sqlalchemy.orm import DeclarativeBase


def generate_uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass
