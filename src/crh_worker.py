#!/usr/bin/env python
"""This cr_hydra worker program - it queries the database and does the actual
processing of simulations (modelings/inversions).

"""
import shutil
import glob
import time
import datetime
import hashlib
import io
from multiprocessing import Process
import logging
import tarfile
import platform
import os
import tempfile
import subprocess
from optparse import OptionParser

import pandas as pd
from sqlalchemy import create_engine
import IPython

from cr_hydra.settings import get_config

IPython

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)

# settings: should be read from config file/cmd
global_settings = get_config()
# [s]
query_interval = 15
# settings end

engine = create_engine(
    global_settings['general']['db_credentials'],
    echo=False, pool_size=1, pool_recycle=3600,
)
node_name = platform.node()
logging.info('Identifying as node: {}'.format(node_name))
results = engine.execute(
    ' '.join((
        'select nice_level, nr_cpus, nr_threads from node_settings',
        'where node_name = %(node_name)s;',
    )),
    node_name=node_name
)
if results.rowcount == 1:
    logging.info('Found node settings in database for node: {}'.format(
        node_name
    ))
    (nice_level, nr_cpus, number_of_worker_threads) = results.fetchone()
    number_of_workers = int(nr_cpus / number_of_worker_threads)
else:
    # hopefully sane defaults
    number_of_workers = 2
    number_of_worker_threads = 2
    nice_level = 20
    results.close()


class hydra_worker(Process):

    def __init__(self, name, cmd_opts, **kwargs):
        Process.__init__(self)
        self.name = name
        self.cmd_opts = cmd_opts
        self.logger = logging.getLogger('crh_worker-' + name)
        self.engine = create_engine(
            global_settings['general']['db_credentials'],
            echo=False, pool_size=10, pool_recycle=3600,
        )

    def run(self):
        """

        """
        while(True):
            if self._check_node_active():
                did_sim = self._query_db_and_run_sim()
                if did_sim:
                    # try to get the next inversion immediately
                    interval = 0
                else:
                    if self.cmd_opts.quit_after_empty:
                        self.logger.info(
                            'thread quitting due to empty db queue ' +
                            '(--quit option)'
                        )
                        return
                    interval = query_interval
            else:
                # sleep 30 seconds
                self.logger.info(
                    'Node was disabled by db, sleeping 30 seconds')
                interval = 30
            time.sleep(interval)

    def _check_node_active(self):
        """Check if this node should be active
        """
        result = self.engine.execute(
            'select active from node_settings where node_name=%(node_name)s;',
            node_name=node_name
        )
        if result.rowcount == 1:
            is_active = result.fetchone()[0]
            return is_active
        else:
            result.close()
        # by default we assume that this node is active
        return True

    def _query_db_and_run_sim(self):
        """
        Returns
        -------
        did_sim: bool
            We want to know if there were simulations to run, e.g., to adapt
            the sleeping interval between db queries
        """
        self.logger.info('Querying DB for new simulations')
        # query database for open inversions
        self.conn = self.engine.connect()
        transaction = self.conn.begin_nested()
        # get the next free, unfinished simulation
        r = self.conn.execute(
            ' '.join((
                'select index from inversions where ',
                'ready_for_processing=\'t\' and status <> \'finished\'',
                'and error=0',
                'order by ',
                'index asc for update skip locked limit 1;'
            ))
        )
        if r.rowcount == 0:
            r.close()
            transaction.commit()
            self.conn.close()
            return False
        # now the row is locked for us
        job_id = r.fetchone()[0]
        self.logger.info('job id: {}'.format(job_id))
        query = ' '.join((
            'select',
            'tomodir_unfinished_file, sim_type,',
            'ready_for_processing, status',
            'from inversions',
            'where index=%(index)s;'
        ))
        job_data = pd.read_sql_query(
            query, self.conn, params={'index': job_id})

        self.logger.info('Processing job id: {}'.format(job_id))

        self._run_sim(
            job_id,
            int(job_data['tomodir_unfinished_file'].values.take(0)),
            # job_data['hydra_location'].values.take(0),
            # job_data['archive_hash'].values.take(0),
            job_data['sim_type'].values.take(0)
        )

        # this actually updates the database
        transaction.commit()
        self.conn.close()
        return True

    def _run_sim(self, job_id, file_id, sim_type):
        tempdir = tempfile.mkdtemp('_crhydra')
        self.logger.info('tempdir: {}'.format(tempdir))

        # get unfinished data and unpack
        result = self.conn.execute(
            'select hash, data from binary_data where index=%(file_id)s;',
            file_id=file_id
        )
        file_hash, binary_data = result.fetchone()

        # check hash
        m = hashlib.sha256()
        m.update(binary_data)
        assert file_hash == m.hexdigest()

        # unpack to tempir
        fid = io.BytesIO(bytes(binary_data))
        with tarfile.open(fileobj=fid, mode='r') as tar:
            tar.extractall(path=tempdir)

        # call td run
        old_pwd = os.getcwd()
        os.chdir(tempdir)
        self.logger.info('Running inversion')
        dt_inv_started = datetime.datetime.now(tz=datetime.timezone.utc)

        inv_cpu = subprocess.check_output(
            'cat /proc/cpuinfo | grep "model name" | head -1',
            shell=True
        )[13:].decode('utf-8').strip()
        # 0: everything ok
        error_code = 0
        try:
            subprocess.check_output(
                'nice -n {} td_run_all_local -n 1 -t {}'.format(
                    nice_level,
                    number_of_worker_threads
                ),
                stderr=subprocess.STDOUT,
                shell=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.error('There was an error executing CRTomo')
            self.logger.error(e)
            # it seems something went wrong while running CRTomo...
            query = ' '.join((
                'update inversions set',
                'error = %(error_code)s,',
                'error_msg=%(error_msg)s,',
                'datetime_inversion_started=%(dt_started)s,',
                'datetime_finished=%(dt_finished)s, ',
                'inv_computer=%(node_name)s,',
                'inv_cpu=%(inv_cpu)s',
                'where index=%(job_id)s;',
            ))
            r = self.conn.execute(
                query,
                {
                    'job_id': job_id,
                    'error_code': 2,
                    'node_name': node_name,
                    'inv_cpu': inv_cpu,
                    'dt_started': dt_inv_started,
                    'dt_finished': datetime.datetime.now(
                        tz=datetime.timezone.utc),
                    'error_msg': e.cmd + '_' + e.output.decode('utf-8'),
                }
            )
            return

        # special case: an error.dat file appeared, indicating that the
        # inversion itself broke. This is seen as a successful simulation
        # from the view of cr_hydra
        tomodir_name = glob.glob(tempdir + '/*')[0]
        error_file = os.sep.join((
            tomodir_name, 'exe', 'error.dat'
        ))
        if os.path.isfile(error_file):
            self.logger.info('found error.dat file - setting error code to 1')
            error_code = 1

        dt_inv_ended = datetime.datetime.now(tz=datetime.timezone.utc)

        self.logger.info('finished')
        # create in-memory archive
        finished_data = io.BytesIO()
        with tarfile.open(fileobj=finished_data, mode='w:xz') as tar_out:
            tar_out.add('.')

        # create hash of final data
        m = hashlib.sha256()
        finished_data.seek(0)
        m.update(finished_data.read())
        hash_final = m.hexdigest()

        # upload
        finished_data.seek(0)
        result = self.conn.execute(
            'insert into binary_data (hash, data) values' +
            '(%(data_hash)s, %(bin_data)s) returning index;',
            data_hash=hash_final,
            bin_data=finished_data.read()
        )
        finished_data_index = result.fetchone()[0]

        os.chdir(old_pwd)
        self.logger.info('updating to finished')
        # mark as finished
        query = ' '.join((
            'update inversions set',
            'status=\'finished\',',
            'error=%(error_code)s,',
            'tomodir_finished_file=%(finished_data)s,',
            'datetime_inversion_started=%(dt_started)s,',
            'datetime_finished=%(dt_finished)s, ',
            'inv_computer=%(node_name)s,',
            'inv_cpu=%(inv_cpu)s',
            'where index=%(job_id)s;',
        ))
        r = self.conn.execute(
            query,
            {
                'job_id': job_id,
                'finished_data': finished_data_index,
                'node_name': node_name,
                'inv_cpu': inv_cpu,
                'error_code': error_code,
                'dt_started': dt_inv_started,
                'dt_finished': dt_inv_ended,
            }
        )
        assert r.rowcount == 1

        # delete temporary directory
        shutil.rmtree(tempdir)

    def _get_hash_sha256(self, filename):
        sha256 = subprocess.check_output(
            'sha256sum "{}"'.format(filename), shell=True).decode('utf-8')
        sha256 = sha256[0:sha256.find(' ')]
        return sha256


def handle_cmd_options():
    parser = OptionParser()
    # parser.add_option(
    #     "-n", "--number",
    #     dest="number_processes",
    #     help="How many CRMod/CRTomo instances to start in parallel. " +
    #     "Default: number of detected CPUs/2",
    #     type='int',
    #     default=None,
    # )

    parser.add_option(
        "-q", "--quit",
        dest="quit_after_empty",
        help="Exit the program when no more simulations are queries in the DB",
        action='store_true',
    )

    (options, args) = parser.parse_args()
    return options


def main():
    cmd_opts = handle_cmd_options()

    workers = []
    for i in range(number_of_workers):
        worker = hydra_worker('thread_{:02}'.format(i), cmd_opts)
        workers.append(worker)
        worker.start()


if __name__ == '__main__':
    main()
