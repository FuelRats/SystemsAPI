from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    JSON
)

from .meta import Base


class System(Base):
    __tablename__ = 'systems'
    id64 = Column(BigInteger, primary_key=True, name='id64')
    name = Column(Text)
    coords = Column(JSON)
    date = Column(DateTime)
    date.info.update({'pyramid_jsonapi': {'visible': False}})
