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

from .meta import Base
from sqlalchemy.dialects.postgresql import JSONB


class Body(Base):
    __tablename__ = 'bodies'
    id64 = Column(BigInteger, primary_key=True)
    bodyId = Column(Integer)
    name = Column(Text)
    type = Column(Text)
    subType = Column(Text)
    parents = Column(JSONB)
    distanceToArrival = Column(Float)
    isLandable = Column(Boolean)
    gravity = Column(Float)
    earthMasses = Column(Float)
    radius = Column(Float)
    surfaceTemperature = Column(Float)
    surfacePressure = Column(Float)
    volcanismType = Column(Text)
    atmosphereType = Column(Text)
    atmosphereComposition = Column(JSONB)
    terraformingState = Column(Text)
    orbitalPeriod = Column(Float)
    semiMajorAxis = Column(Float)
    orbitalEccentricity = Column(Float)
    orbitalInclination = Column(Float)
    argOfPeriapsis = Column(Float)
    rotationalPeriod = Column(Float)
    rotationalPeriodTidallyLocked = Column(Boolean)
    axialTilt = Column(Float)
    rings = Column(JSONB)
    materials = Column(JSONB)
    updateTime = Column(DateTime)
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    systemName = Column(Text)


Index('body_idx_id64', Body.id64, unique=True)
Index('body_idx_systemid64', Body.systemId64)
