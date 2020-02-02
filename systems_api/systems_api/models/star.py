from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    Float,
    Integer,
    ForeignKey,
    JSON
)

from .meta import Base


class Star(Base):
    __tablename__ = 'stars'
    id64 = Column(BigInteger, primary_key=True)
    bodyId = Column(Integer)
    name = Column(Text)
    discovery = Column(JSON)
    type = Column(Text)
    subType = Column(Text)
    offset = Column(Integer)
    parents = Column(JSON)
    distanceToArrival = Column(Float)
    isMainStar = Column(Boolean)
    isScoopable = Column(Boolean)
    age = Column(BigInteger)
    luminosity = Column(Text)
    absoluteMagnitude = Column(Float)
    solarMasses = Column(Float)
    solarRadius = Column(Float)
    surfaceTemperature = Column(BigInteger)
    volcanismType = Column(Text)
    atmosphereType = Column(Text)
    terraformingState = Column(Text)
    orbitalPeriod = Column(Float)
    semiMajorAxis = Column(Float)
    orbitalEccentricity = Column(Float)
    orbitalInclination = Column(Float)
    argOfPeriapsis = Column(Float)
    rotationalPeriod = Column(Float)
    rotationalPeriodTidallyLocked = Column(Boolean)
    axialTilt = Column(Float)
    belts = Column(JSON)
    updateTime = Column(DateTime)
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    systemName = Column(Text)
