from sqlalchemy import (
    Column,
    BigInteger,
    Text
)

from .meta import Base


class Permits(Base):
    __tablename__ = 'permit_systems'
    id64 = Column(BigInteger, primary_key=True)
    permit_name = Column(Text)

