#!/usr/bin/env python
from sqlalchemy import create_engine
import json
database_login = 'postgresql://mweigand:mweigand@localhost/cr_hydra'
engine = create_engine(
    database_login, echo=False, pool_size=10, pool_recycle=3600,
)
settings = json.load(open('node_settings.json', 'r'))
for node_name in settings.keys():
    query = ' '.join((
        'insert into node_settings',
        '(node_name, nice_level, nr_cpus, nr_threads)',
        'values',
        '(%(node_name)s, %(nice_level)s, %(nr_cpus)s, %(nr_threads)s)',
        'on conflict do nothing;'
    ))
    node_setting = settings[node_name]
    node_setting['node_name'] = node_name
    print(node_setting)
    engine.execute(query, node_setting)
