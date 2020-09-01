#!/usr/bin/env python
import sys
import json
import logging

from sqlalchemy import create_engine

from cr_hydra.settings import get_config

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)


def main():
    # settings: should be read from config file/cmd
    global_settings = get_config()

    engine = create_engine(
        global_settings['general']['db_credentials'],
        echo=False, pool_size=1, pool_recycle=3600,
    )

    crh_file = sys.argv[1]

    with open(crh_file, 'r') as fid:
        settings = json.load(fid)
    print(crh_file)
    print(settings)

    file_id = settings['tomodir_unfinished_file']

    result = engine.execute(
        'select data from binary_data where index=%(file_id)s;',
        file_id=file_id
    )
    assert result.rowcount == 1
    data = result.fetchone()[0]

    outfile = crh_file + '.tar.xz'
    with open(outfile, 'wb') as fid:
        fid.write(data)

    # check if an inversion is present
    sim_id = settings['sim_id']
    result = engine.execute(
        ' '.join((
            'select tomodir_finished_file from inversions',
            'where index=%(sim_id)s and status=\'finished\'',
            'and downloaded=\'f\'',
            ';'
        )),
        sim_id=sim_id
    )
    assert result.rowcount == 1
    tomodir_finished_file = result.fetchone()[0]

    result = engine.execute(
        'select hash, data from binary_data where index=%(data_id)s;',
        data_id=tomodir_finished_file
    )
    assert result.rowcount == 1
    file_hash, binary_data = result.fetchone()

    outfile = crh_file + '_finished.tar.xz'
    with open(outfile, 'wb') as fid:
        fid.write(binary_data)
