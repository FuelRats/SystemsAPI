from sqlalchemy import (
    Column,
    Float,
    Text
)

from .meta import Base


class Landmark(Base):
    __tablename__ = 'landmarks'
    name = Column(Text, primary_key=True)
    x = Column(Float)
    y = Column(Float)
    z = Column(Float)
    soi = Column(Float)
