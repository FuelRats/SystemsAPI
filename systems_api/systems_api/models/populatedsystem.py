from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Index
)

from sqlalchemy.dialects.postgresql import JSONB

from .meta import Base


class PopulatedSystem(Base):
    __tablename__ = 'populated_systems'
    id64 = Column(BigInteger, doc="64-bit system ID", primary_key=True)
    name = Column(Text, doc="System name")
    coords = Column(JSONB, doc="System coordinates, as a JSON blob with X,Y and Z coordinates as floats.")
    controllingFaction = Column(JSONB, doc="Controlling faction, in a JSON blob")
    date = Column(DateTime, doc="DateTime of last update to this system")
    date.info.update({'pyramid_jsonapi': {'visible': False}})


Index('psystem_idx_id64', PopulatedSystem.id64, unique=True)
Index('psystem_idx_systemid64', PopulatedSystem.name)
