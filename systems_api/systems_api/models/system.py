from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Index,
    Float,
    func)

from sqlalchemy.dialects.postgresql import JSONB
from .meta import Base


class System(Base):
    __tablename__ = 'systems'
    id64 = Column(BigInteger, primary_key=True, name='id64')
    name = Column(Text)
    coords = Column(JSONB)
    date = Column(DateTime)
    date.info.update({'pyramid_jsonapi': {'visible': False}})


Index('system_idx_id64', System.id64, unique=True)
Index('system_idx_name_gin', System.name, postgresql_using='gin',
      postgresql_ops={'name': 'gin_trgm_ops'})
Index('system_idx_name_btree', System.name, postgresql_using='btree')
Index('system_idx_name_soundex', System.name, postgresql_using='soundex')
Index('system_idx_name_dmetaphone', System.name, postgresql_using='dmetaphone')
Index('system_idx_coords_x', System.coords['x'].cast(Float))
Index('system_idx_coords_y', System.coords['y'].cast(Float))
Index('system_idx_coords_z', System.coords['z'].cast(Float))

