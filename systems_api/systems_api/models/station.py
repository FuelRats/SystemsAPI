from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey)

from sqlalchemy.dialects.postgresql import JSONB

from .meta import Base


class Station(Base):
    __tablename__ = 'stations'
    id64 = Column(BigInteger, primary_key=True)
    marketId = Column(BigInteger)
    type = Column(Text)
    name = Column(Text)
    distanceToArrival = Column(Float)
    allegiance = Column(Text)
    government = Column(Text)
    economy = Column(Text)
    haveMarket = Column(Boolean)
    haveShipyard = Column(Boolean)
    haveOutfitting = Column(Boolean)
    otherServices = Column(JSONB)
    stationState = Column(Text)
    updateTime = Column(DateTime)
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    systemName = Column(Text)
