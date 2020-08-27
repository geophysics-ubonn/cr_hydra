#!/usr/bin/env python
# *-* coding: utf-8 *-*
"""Look for all unfinished tomodirs in the present directory (and
subdirectories), e called.
"""
import shutil
import uuid
import os
import datetime
import json
import tarfile
import subprocess
import platform
# import pandas as pd
from sqlalchemy import create_engine
from optparse import OptionParser
import IPython
IPython


def handle_cmd_options():
    parser = OptionParser()
    # parser.add_option(
    #     '-t', "--threads",
    #     dest="number_threads",
    #     type="int",
    #     help="number of threads EACH CRMod/CRTomo instance uses. If not " +
    #     "set, will be determined automatically",
    #     default=None,
    # )

    # parser.add_option(
    #     "-n", "--number",
    #     dest="number_processes",
    #     help="How many CRMod/CRTomo instances to start in parallel. " +
    #     "Default: number of detected CPUs/2",
    #     type='int',
    #     default=None,
    # )

    # parser.add_option(
    #     "-r", "--reverse",
    #     dest="reverse_lists",
    #     help="Reverse directory lists before working with them",
    #     action='store_true',
    # )

    (options, args) = parser.parse_args()
    return options


def is_tomodir(subdirectories):
    """provided with the subdirectories of a given directory, check if this is
    a tomodir
    """
    required = (
        'exe',
        'config',
        'rho',
        'mod',
        'inv'
    )
    is_tomodir = True
    for subdir in required:
        if subdir not in subdirectories:
            is_tomodir = False
    return is_tomodir


def check_if_needs_modeling(tomodir):
    """check of we need to run CRMod in a given tomodir
    """
    print('check for modeling', tomodir)
    required_files = (
        'config' + os.sep + 'config.dat',
        'rho' + os.sep + 'rho.dat',
        'grid' + os.sep + 'elem.dat',
        'grid' + os.sep + 'elec.dat',
        'exe' + os.sep + 'crmod.cfg',
    )

    not_allowed = (
        'mod' + os.sep + 'volt.dat',
    )
    needs_modeling = True
    for filename in not_allowed:
        if os.path.isfile(tomodir + os.sep + filename):
            needs_modeling = False

    for filename in required_files:
        full_file = tomodir + os.sep + filename
        if not os.path.isfile(full_file):
            print('does not exist: ', full_file)
            needs_modeling = False

    return needs_modeling


def check_if_needs_inversion(tomodir):
    """check of we need to run CRTomo in a given tomodir

    Parameters
    ----------
    tomodir : str
        Tomodir to check

    Returns
    -------
    needs_inversion : bool
        True if not finished yet
    """
    required_files = (
        'grid' + os.sep + 'elem.dat',
        'grid' + os.sep + 'elec.dat',
        'exe' + os.sep + 'crtomo.cfg',
    )

    needs_inversion = True

    for filename in required_files:
        if not os.path.isfile(tomodir + os.sep + filename):
            needs_inversion = False

    # check for crmod OR modeling capabilities
    if not os.path.isfile(tomodir + os.sep + 'mod' + os.sep + 'volt.dat'):
        if not check_if_needs_modeling(tomodir):
            print('no volt.dat and no modeling possible')
            needs_inversion = False

    # check if finished
    inv_ctr_file = tomodir + os.sep + 'inv' + os.sep + 'inv.ctr'
    if os.path.isfile(inv_ctr_file):
        inv_lines = open(inv_ctr_file, 'r').readlines()
        print('inv_lines', inv_lines[-1])
        if inv_lines[-1].startswith('***finished***'):
            needs_inversion = False

    return needs_inversion


def find_unfinished_tomodirs(directory):
    needs_modeling = []
    needs_inversion = []
    for root, dirs, files in os.walk(directory):
        dirs.sort()
        if is_tomodir(dirs):
            print('found tomodir: ', root)
            if check_if_needs_modeling(root):
                needs_modeling.append(root)
            if check_if_needs_inversion(root):
                needs_inversion.append(root)

    return sorted(needs_modeling), sorted(needs_inversion)


def _register_tomodir_for_processing(tomodir_raw, sim_type):
    """
    sim_type: inv|mod
    """
    tomodir = os.path.abspath(tomodir_raw)
    # should be read from the configuration file
    username = 'mweigand'

    crh_file = tomodir + '.crh'
    if os.path.isfile(crh_file):
        # do nothing - assume another process is working with this tomodir
        return

    crh_settings = {
        'datetime_init': '{}'.format(
            datetime.datetime.now(tz=datetime.timezone.utc)
         ),
    }
    # touch the crh file as a crude locking mechanism
    with open(crh_file, 'w') as fid:
        json.dump(crh_settings, fid)

    # create archive
    pwdx = os.getcwd()
    os.chdir(os.path.dirname(tomodir))

    tomodir_id = username + '_' + str(uuid.uuid4())
    archive_file = os.path.abspath(tomodir_id + '.tar.xz')
    with tarfile.open(archive_file, 'w:xz') as tar:
        tar.add(os.path.basename(tomodir), recursive=True)
    os.chdir(pwdx)

    # prepare data for simulation registration
    # crh_settings['archive_file'] = os.path.basename(archive_file)
    # crh_settings['archive_hash'] = sha256
    crh_settings['source_computer'] = platform.node()
    crh_settings['sim_type'] = sim_type
    # hydra_dir
    # hydra_dir = '/home/mweigand/hydra'
    # crh_settings['hydra_location'] = hydra_dir + os.sep + os.path.basename(
    #   # archive_file)
    crh_settings['crh_file'] = os.path.abspath(crh_file)
    crh_settings['username'] = username

    engine = create_engine(
        'postgresql://mweigand:mweigand@localhost/cr_hydra',
        echo=False,
        pool_size=10,
        pool_recycle=3600,
    )

    # upload archive to database
    query = ' '.join((
        'insert into binary_data (filename, hash, data) values',
        '(%(filename)s, %(file_hash)s, %(bin_data)s) returning index;'
    ))
    import psycopg2
    sha256 = subprocess.check_output(
        'sha256sum "{}"'.format(archive_file), shell=True).decode('utf-8')
    sha256 = sha256[0:sha256.find(' ')]

    result = engine.execute(
        query,
        filename=os.path.basename(archive_file),
        file_hash=sha256,
        bin_data=psycopg2.Binary(open(archive_file, 'rb').read())
    )
    assert result.rowcount == 1
    file_id = result.fetchone()[0]
    crh_settings['tomodir_unfinished_file'] = file_id
    # IPython.embed()
    # exit()
    query = ' '.join((
        'insert into inversions (',
        'username,',
        'datetime_init,',
        'tomodir_unfinished_file,',
        'source_computer,',
        'sim_type,',
        'crh_file',
        ') values (',
        '%(username)s,',
        '%(datetime_init)s,',
        '%(tomodir_unfinished_file)s,',
        '%(source_computer)s,',
        '%(sim_type)s,',
        '%(crh_file)s',
        ')',
        'returning index;'
    ))
    result = engine.execute(
        query,
        crh_settings
    )
    assert result.rowcount == 1
    sim_id = result.fetchone()[0]
    print(query)
    crh_settings['sim_id'] = sim_id
    # update crh file
    with open(crh_file, 'w') as fid:
        json.dump(crh_settings, fid, sort_keys=True, indent=4)
    # now move the archive file to the hydra directory
    # shutil.move(archive_file, crh_settings['hydra_location'])
    os.unlink(archive_file)
    # now we are ready for processing
    engine.execute(
        'update inversions set '
        'ready_for_processing=\'t\' where index=%(id)s;', {'id': sim_id}
    )
    # delete tomodir
    shutil.rmtree(tomodir)


def main():
    # options = handle_cmd_options()
    needs_modeling, needs_inversion = find_unfinished_tomodirs('.')
    print('-' * 20)
    print('modeling:', needs_modeling)
    print('inversion:', needs_inversion)
    print('-' * 20)
    for directory in needs_modeling:
        _register_tomodir_for_processing(directory, 'mod')
    for directory in needs_inversion:
        _register_tomodir_for_processing(directory, 'inv')
    # IPython.embed()


if __name__ == '__main__':
    main()
