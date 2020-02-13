from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    Float,
    Integer,
    ForeignKey,
    Index
)

from sqlalchemy.dialects.postgresql import JSONB

from .meta import Base


class Star(Base):
    __tablename__ = 'stars'
    id64 = Column(BigInteger, primary_key=True)
    bodyId = Column(Integer)
    name = Column(Text)
    type = Column(Text)
    subType = Column(Text)
    parents = Column(JSONB)
    distanceToArrival = Column(Float)
    isMainStar = Column(Boolean)
    isScoopable = Column(Boolean)
    age = Column(BigInteger)
    luminosity = Column(Text)
    absoluteMagnitude = Column(Float)
    solarMasses = Column(Float)
    solarRadius = Column(Float)
    surfaceTemperature = Column(Float)
    orbitalPeriod = Column(Float)
    semiMajorAxis = Column(Float)
    orbitalEccentricity = Column(Float)
    orbitalInclination = Column(Float)
    argOfPeriapsis = Column(Float)
    rotationalPeriod = Column(Float)
    rotationalPeriodTidallyLocked = Column(Boolean)
    axialTilt = Column(Float)
    belts = Column(JSONB)
    updateTime = Column(DateTime)
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    systemName = Column(Text)


Index('star_idx_id64', Star.id64, unique=True)
Index('star_idx_systemid64', Star.systemId64)
