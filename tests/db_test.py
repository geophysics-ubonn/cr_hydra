#!/usr/bin/env python

from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://mweigand:mweigand@localhost/cr_hydra',
    echo=False,
    pool_size=10,
    pool_recycle=3600,
)


