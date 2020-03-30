from sqlalchemy import (
    Column,
    Integer,
    Text
)

from .meta import Base


class Stats(Base):
    __tablename__ = 'stats'
    lastupdate = Column(Integer, primary_key=True)
    syscount = Column(Integer)
    starcount = Column(Integer)
    bodycount = Column(Integer)
