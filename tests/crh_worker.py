#!/usr/bin/env python
from sqlalchemy import create_engine

# settings
number_of_workers = 2
number_of_worker_threads = 2
database_login = 'postgresql://mweigand:mweigand@localhost/cr_hydra'
work_directory = '/tmp'


class hydra_worker(object):

    def __init__(self, settings):
        self.settings = settings
        self.engine = create_engine(
            database_login, echo=False, pool_size=10, pool_recycle=3600,
        )

    def run(self):
        # query database for open inversions
        conn = engine.connect()
        conn.begin_nested()
        r = conn.execute(
            'select index from inversions where '
            'ready_for_processing=\'t\' and status <> \'a\' order by '
            'index desc for update skip locked limit 1;'
        )
        # now the row is locked for us

        # download, invert, upload, then change status, and finally, close
        conn.close()



if __name__ == '__main__':
    pass
