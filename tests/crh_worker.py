#!/usr/bin/env python
"""

"""
from multiprocessing import Process
# import threading
import logging
import tarfile
import os
import tempfile
import shutil
import pandas as pd
import subprocess
from sqlalchemy import create_engine
import IPython
IPython

logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {name} - %{levelname} - {message}',
    style='{',
)

# settings: should be read from config file/cmd
number_of_workers = 2
number_of_worker_threads = 2
database_login = 'postgresql://mweigand:mweigand@localhost/cr_hydra'
work_directory = './'
# settings end


class hydra_worker(Process):

    def __init__(self, name, settings, **kwargs):
        print('init worker')
        Process.__init__(self)
        self.name = name
        self.settings = settings
        self.logger = logging.getLogger(name)
        self.engine = create_engine(
            database_login, echo=False, pool_size=10, pool_recycle=3600,
        )

    def run(self):
        """

        """
        print('run')
        # query database for open inversions
        conn = self.engine.connect()
        transaction = conn.begin_nested()
        r = conn.execute(
            'select index from inversions where '
            'ready_for_processing=\'t\' and status <> \'finished\' order by '
            'index desc for update skip locked limit 1;'
        )
        # now the row is locked for us
        if r.rowcount == 0:
            return
        job_id = r.fetchone()[0]
        self.logger.info('job id: {}'.format(job_id))
        query = ' '.join((
            'select',
            'archive_file, archive_hash, sim_type, hydra_location,'
            'ready_for_processing, status',
            'from inversions',
            'where index=%(index)s;'
        ))
        job_data = pd.read_sql_query(query, conn, params={'index': job_id})

        self.logger.info('Processing job id: {}'.format(job_id))
        sim_result = self._run_sim(
            job_data['hydra_location'].values.take(0),
            job_data['archive_hash'].values.take(0),
            job_data['sim_type'].values.take(0)
        )
        # sim_result = True
        if sim_result:
            self.logger.info('updating to finished')
            # mark as finished
            query = ' '.join((
                'update inversions set status=\'finished\' where',
                'index=%(job_id)s;',
            ))
            print(query, job_id)
            r = conn.execute(query, {'job_id': job_id})
            # print(r.rowcount)
            # IPython.embed()

        transaction.commit()
        conn.close()

    def _run_sim(self, remote_file, file_hash, sim_type):
        self.logger.info(remote_file)
        tempdir = tempfile.mkdtemp('_crhydra')
        self.logger.info('tempdir: {}'.format(tempdir))
        outfile = tempdir + os.sep + os.path.basename(remote_file)
        shutil.copy(remote_file, outfile)
        # make sure the hashes compare
        assert self._get_hash_sha256(outfile) == file_hash
        # unpack
        archive = tarfile.open(outfile, 'r')
        archive.extractall(tempdir)

        # call td run
        old_pwd = os.getcwd()
        tomodir_name = archive.getnames()[0]
        os.chdir(tempdir + os.sep + tomodir_name)
        self.logger.info('Running inversion')
        subprocess.check_output(
            'td_run_all_local -n 1 -t {}'.format(number_of_worker_threads),
            shell=True
        )
        self.logger.info('finished')

        os.chdir('..')
        self.logger.info('archiving results: {}'.format(os.getcwd()))
        archive_file = os.path.abspath(
            os.path.basename(outfile) + '.crh_finished'
        )
        print(os.getcwd(), archive_file, tomodir_name)
        with tarfile.open(archive_file, 'w:xz') as tar:
            tar.add(tomodir_name, recursive=True)

        self.logger.info('moving archive')
        final_file = os.path.dirname(
            remote_file) + os.sep + os.path.basename(archive_file)
        shutil.move(
            archive_file,
            final_file,
        )

        # TODO: probably a few checks would be in order
        os.chdir(old_pwd)
        # import IPython
        # IPython.embed()
        return True

    def _get_hash_sha256(self, filename):
        sha256 = subprocess.check_output(
            'sha256sum "{}"'.format(filename), shell=True).decode('utf-8')
        sha256 = sha256[0:sha256.find(' ')]
        return sha256


if __name__ == '__main__':
    worker1 = hydra_worker('thread1', {})
    worker2 = hydra_worker('thread2', {})
    worker1.start()
    worker2.start()
    print('end')
