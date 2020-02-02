from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Boolean,
    Float,
    Integer,
    ForeignKey,
    JSON)

from .meta import Base


class Body(Base):
    __tablename__ = 'bodies'
    id64 = Column(BigInteger, primary_key=True)
    bodyId = Column(Integer)
    name = Column(Text)
    discovery = Column(JSON)
    type = Column(Text)
    subType = Column(Text)
    offset = Column(Integer)
    parents = Column(JSON)
    distanceToArrival = Column(Float)
    isLandable = Column(Boolean)
    gravity = Column(Float)
    earthMasses = Column(Float)
    radius = Column(Float)
    surfaceTemperature = Column(Float)
    surfacePressure = Column(Float)
    volcanismType = Column(Text)
    atmosphereType = Column(Text)
    atmosphereComposition = Column(JSON)
    terraformingState = Column(Text)
    orbitalPeriod = Column(Float)
    semiMajorAxis = Column(Float)
    orbitalEccentricity = Column(Float)
    orbitalInclination = Column(Float)
    argOfPeriapsis = Column(Float)
    rotationalPeriod = Column(Float)
    rotationalPeriodTidallyLocked = Column(Boolean)
    axialTilt = Column(Float)
    rings = Column(JSON)
    materials = Column(JSON)
    updateTime = Column(DateTime)
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    systemName = Column(Text)
