from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    DateTime,
    Index,
    Float,
    func, text)

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
#Index('system_idx_name_soundex', System.name, postgresql_using='btree',
#      postgresql_ops={''})
#Index('system_idx_name_dmetaphone', System.name, postgresql_using='dmetaphone')
Index('system_idx_coords_x', text("(coords->'x') jsonb_path_ops"), postgresql_using='gin')
Index('system_idx_coords_y', text("(coords->'y') jsonb_path_ops"), postgresql_using='gin')
Index('system_idx_coords_z', text("(coords->'z') jsonb_path_ops"), postgresql_using='gin')
