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


class Carrier(Base):
    """Represents a player-owned Carrier."""
    __tablename__ = 'carriers'
    callsign = Column(Text, primary_key=True)
    """Callsign of the Carrier. Primary key."""
    marketId = Column(BigInteger)
    """Market ID of the carrier."""
    name = Column(Text)
    """Name of the carrier."""
    dockingAccess = Column(Text)
    """Who can dock on the carrier."""
    dockingCriminals = Column(Boolean)
    """Whether players with notoriety can dock."""
    distanceToArrival = Column(Float)
    """Distance to carrier from system's barycenter."""
    haveMarket = Column(Boolean)
    """Whether the carrier has a market. Should always be true."""
    haveShipyard = Column(Boolean)
    """Whether the carrier has a shipyard."""
    haveOutfitting = Column(Boolean)
    """Whether the carrier has outfitting services."""
    haveRearm = Column(Boolean)
    """Whether the carrier has rearm services."""
    haveRefuel = Column(Boolean)
    """Whether the carrier has refuel services."""
    haveContacts = Column(Boolean)
    """Whether the carrier has voucher redemption."""
    haveBlackMarket = Column(Boolean)
    """Whether the carrier has a black market."""
    otherServices = Column(JSONB)
    """Other services the carrier has"""
    updateTime = Column(DateTime)
    """Last update time of the carrier's data"""
    updateTime.info.update({'pyramid_jsonapi': {'visible': False}})
    systemId64 = Column(BigInteger, ForeignKey('systems.id64'))
    """ID64 of the system the carrier is in."""
    systemName = Column(Text)
    """Name of the system the carrier is in."""
