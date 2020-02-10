from sqlalchemy import (
    Column,
    BigInteger
)

from .meta import Base


class Permits(Base):
    __tablename__ = 'permit_systems'
    id64 = Column(BigInteger, primary_key=True)

