#!/usr/bin/env python
from sqlalchemy import create_engine

database_login = 'postgresql://mweigand:mweigand@localhost/cr_hydra'
engine = create_engine(
    database_login, echo=False, pool_size=10, pool_recycle=3600,
)

result = engine.execute(
    'select filename, hash, data from binary_data;',
)
print('total count:', result.rowcount)

for nr, row in enumerate(result):
    print(row)
    if row[2] is not None:
        if row[0] is None:
            filename = 'result_{:02}.tar.xz'.format(nr)
        else:
            filename = row[0]

        with open(filename, 'wb') as fid:
            fid.write(bytes(row[2]))
