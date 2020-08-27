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

from sqlalchemy import create_engine
import IPython
IPython

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__name__)

# settings: should be read from config file/cmd
number_of_workers = 2
number_of_worker_threads = 2
database_login = 'postgresql://mweigand:mweigand@localhost/cr_hydra'
work_directory = './'
query_interval = 5
# settings end

engine = create_engine(
    database_login, echo=False, pool_size=10, pool_recycle=3600,
)


def _is_finished(sim_id):
    result = engine.execute(
        'select tomodir_finished_file from inversions ' +
        'where index=%(sim_id)s and status=\'finished\' ' +
        'and downloaded=\'f\';',
        sim_id=sim_id
    )
    if result.rowcount == 1:
        return result.fetchone()[0]
    else:
        return None


def _check_and_retrieve(filename):
    logger.info('Checking: {}'.format(filename))
    sim_settings = json.load(open(filename, 'r'))
    print(sim_settings)
    final_data_id = _is_finished(sim_settings['sim_id'])

    tomodir_name = os.path.basename(filename)[:-4]
    basedir = os.path.dirname(filename)

    pwd = os.getcwd()

    if final_data_id is not None:
        # we got data
        result = engine.execute(
            'select hash, data from binary_data where index=%(data_id)s;',
            data_id=final_data_id
        )
        assert result.rowcount == 1
        file_hash, binary_data = result.fetchone()

        # check hash
        m = hashlib.sha256()
        m.update(binary_data)
        assert file_hash == m.hexdigest()

        os.chdir(basedir)

        # unpack
        fid = io.BytesIO(bytes(binary_data))
        with tarfile.open(fileobj=fid, mode='r') as tar:
            # tar.extractall(path=tempdir)
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
        mark_sim_as_downloaded(sim_settings['sim_id'])
        os.unlink(filename)
        # IPython.embed()


def mark_sim_as_downloaded(sim_id):
    # mark the simulation as downloaded and delete the files
    result = engine.execute(
        'select tomodir_unfinished_file, tomodir_finished_file from ' +
        'inversions where index=%(sim_id)s;',
        sim_id=sim_id
    )
    assert result.rowcount == 1
    file_ids = list(result.fetchone())
    print(file_ids, type(file_ids))
    result = engine.execute(
        'update inversions set ' +
        'tomodir_unfinished_file=NULL, ' +
        'tomodir_finished_file=NULL, ' +
        'downloaded=\'t\' where index=%(sim_id)s;',
        sim_id=sim_id
    )
    assert result.rowcount == 1
    # delete
    result = engine.execute(
        'delete from binary_data where index in (%(id1)s, %(id2)s);',
        id1=file_ids[0],
        id2=file_ids[1],
    )


if __name__ == '__main__':
    # walk the current directory
    for root, dirs, files in os.walk('.'):
        dirs.sort()
        files.sort()
        for filename in files:
            if filename.endswith('.crh'):
                _check_and_retrieve(root + os.sep + filename)
