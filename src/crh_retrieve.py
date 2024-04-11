#!/usr/bin/env python
"""
check the database for inversions
"""
import logging
import os
import hashlib
import io
import tarfile
import json

from sqlalchemy import create_engine, text
import IPython

from cr_hydra.settings import get_config

IPython

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__name__)

global_settings = get_config()

engine = create_engine(
    global_settings['general']['db_credentials'],
    echo=False, pool_size=10, pool_recycle=60,
)


def _is_finished(sim_id, conn):
    """Check if the simulation has been processed.

    Ignore any rows already locked by other processes (i.e., concurrent runs
    of crh_retrieve)

    """
    result = conn.execute(
        text(
            ' '.join((
                'select tomodir_finished_file from inversions',
                'where index=:sim_id and status=\'finished\'',
                'and downloaded=\'f\'',
                'for update',
                'skip locked',
                ';'
            ))
        ),
        parameters={
            'sim_id': sim_id,
        }
    )
    if result.rowcount == 1:
        return result.fetchone()[0]
    else:
        result.close()
        return None


def _check_and_retrieve(filename):
    """For a given .crh file, check if the inversion results are ready to be
    downloaded and extract the results
    """
    logger.info('Checking: {}'.format(filename))
    sim_settings = json.load(open(filename, 'r'))
    # ignore any simulation not successfully uploade
    if 'sim_id' not in sim_settings:
        return False

    conn = engine.connect()
    # transaction = conn.begin_nested()

    final_data_id = _is_finished(sim_settings['sim_id'], conn)

    tomodir_name = os.path.basename(filename)[:-4]
    basedir = os.path.abspath(os.path.dirname(filename))

    pwd = os.getcwd()

    if final_data_id is not None:
        # we got data
        result = conn.execute(
            text(
                'select hash, data from binary_data where index=:data_id;'
            ),
            parameters={
                'data_id': final_data_id,
            },
        )
        assert result.rowcount == 1
        file_hash, binary_data = result.fetchone()

        # check hash
        m = hashlib.sha256()
        m.update(binary_data)
        assert file_hash == m.hexdigest()

        logger.info('retrieving and unpacking')
        os.chdir(basedir)

        # unpack
        fid = io.BytesIO(bytes(binary_data))
        with tarfile.open(fileobj=fid, mode='r') as tar:
            assert os.path.abspath(os.getcwd()) == os.path.abspath(basedir)

            # make sure there are only files in the archive that go into the
            # tomodir
            for entry in tar.getnames():
                if entry == '.':
                    continue
                # strip leading './'
                if entry.startswith('./'):
                    entry = entry[2:]
                if not entry.startswith(tomodir_name):
                    raise Exception('Content should go into tomodir')
            # now extract
            tar.extractall('.')
        os.chdir(pwd)
        mark_sim_as_downloaded(sim_settings['sim_id'], conn)
        os.unlink(filename)
        # IPython.embed()
    # transaction.commit()
    conn.close()
    engine.dispose()


def mark_sim_as_downloaded(sim_id, conn):
    # mark the simulation as downloaded and delete the files
    result = conn.execute(
        text(
            'select tomodir_unfinished_file, tomodir_finished_file from ' +
            'inversions where index=:sim_id;'
        ),
        parameters={
            'sim_id': sim_id,
        }
    )
    assert result.rowcount == 1
    file_ids = list(result.fetchone())
    result = conn.execute(
        text(
            'update inversions set ' +
            'tomodir_unfinished_file=NULL, ' +
            'tomodir_finished_file=NULL, ' +
            'downloaded=\'t\' where index=:sim_id;'
        ),
        parameters={
            'sim_id': sim_id,
        },
    )
    conn.commit()
    assert result.rowcount == 1
    result.close()
    # delete
    result = conn.execute(
        text('delete from binary_data where index in (:id1, :id2);'),
        parameters={
            'id1': file_ids[0],
            'id2': file_ids[1],
        },
    )
    conn.commit()
    result.close()


def main():
    for root, dirs, files in os.walk('.'):
        dirs.sort()
        files.sort()
        for filename in files:
            if filename.endswith('.crh'):
                _check_and_retrieve(root + os.sep + filename)
                print(engine.pool.status())


if __name__ == '__main__':
    main()
