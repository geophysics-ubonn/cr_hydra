# CRHydra - A distributed modeling/inversion framework for CRMod/CRTomo

## TODO

* Implement a check for the database:
	* duplicate entries (hash, crh_file)

## Introduction

## Definition of terms

* client: A computer on which a modeling/inversion is requested
* host: A central computer on which the primary database used to control the
  cluster is hosted
* worker: A computer on which the worker program of CRHydra runs, doing actual
  modeling/inversions

## Configuration file

A configuration file is required for cr_hydra to be used, containing
information such as:

* location and access information to database
* [not used at this point] Username (and password)

## Planned commands

* crh_add - find all tomodirs in all subdirectories and queue to database
* crh_worker - query the database and run inversions
* crh_retrieve - find all .crh files and check if the corresponding inversions
  				 were already finished. Then download and unpack the results.
* [not implemented] crh_db_cleanup - check the database for stale entries
  (i.e., outstanding simulations without corresponding archive files)
* [not implemented] crh_status - provide information about the queue and
  running inversions

## Rough outline of functionality

* The client requests a given tomodir/sipdir to be processed by running
  *crh_add* on the corresponding directory
* For each tomodir/sipdir  [IN] (depending on the settings):
	* If a control file [IN].crh is present, assume this directory is being
	  processed at the moment, report it and do nothing (unless directory to)
	* A control file (json-format) [IN].crh is created with content:
		* datetime of creation, indicating a registration process is in process
	* A unique id is assigned (comprised of user name and random uuid): [ID]
	* The target dir is compressed with the output file comprised of the id and
	  ending tar.gz [ID].tar.gz (alternative compression algorithms can be
	  used)
	* The simulation is registered in the cr_hydra database and gets assigned a
	  simulation id [SIM_ID], corresponding to the row id of the primary
	  database table, indicating that it is still in the process of being
	  processed. Data provided to database:

	  	* [ID]
		* filename of compressed file
		* sha256 hash of file
		* client computer name
		* datetime of registration
		* final location of simulation data
		* location/name of crh file
		* What type of simulation is requested (modeling or inversion)

	* The control file [IN].crh is filled with content:

		* datetime of registration
		* client computer name
		* sim_id
		* final location of simulation data

	* Move the compressed simulation data to the globally accessible queue
	  directory (e.g., on /users/data)
	* Update database entry that this simulation is ready to be processed

* On each worker computer, after configuration, run crh_worker (with
  corresponding command line parameters). This worker will then contact the
  server an start processing the inversions.

  After finishing an inversion, the result is compressed again and moved to the
  location of the original archive, with ending .crh_finished.

  Then the database is updated with the final result file.

  * Worker options/settings:

	* database login
	* number of concurrent workers
	* number of threads per worker
	*

* On the client computer, crh_retrieve or crh_wait_retrieve can be used to
  query the database for finished inversions, which will be transferred back
  and decompressed.

## Database configuration

* CREATE USER mweigand WITH PASSWORD 'mweigand' CREATEDB;
* create database cr_hydra owner mweigand;
* psql postgresql://mweigand:mweigand@localhost/cr_hydra -f tables.sql
* Get size of data table:

	SELECT pg_size_pretty( pg_total_relation_size('binary_data') );

* get number of row locks for table inversions (indicating the number of active
  inversions):

	select count(relation::regclass) from pg_catalog.pg_locks l left join
	pg_catalog.pg_database db on (db.oid = l.database) where datname='cr_hydra'
	AND NOT pid = pg_backend_pid() and mode=    'RowShareLock';

## Possible problems

* dead inversions in the database: If the .crh files are deleted in the file
  system, currently there is now way to properly remove the corresponding
  orphaned inversions in the database.

  Multiple solutions come mind:

	* if the source computer and the file system can be accessed, a command
	  crh_cleanup could check all inversions of the source computer for
	  existing .crh files
	* inversions could have a life time after which they need to be downloaded
	  (i.e., 30 days after finish/upload of the inversion to the db)

## Ideas

### Thread pool and number of workers

We could try to better facilitate the number of threads to use by analyzing the
inversions for 2 or 2.5 D: In the 2D case only one thread is required per
inversion, while for 2.5D we can use more threads for each inversion.
This would, however, require to actively start and stop threads in reaction to
the currently running inversions.

### Groups

I think it would be nice to introduce groups and restrict certain workers to
certain groups. That way we could implement a local-only worker interface:

	crh_add --with-local_inv

would then query the inversions using a newly (randomly generated) group and
spawn a local crh_worker

	crh_worker --group %(group)s --quit

which in turn would on only work on the given group and quit itself after
running all inversions in the group.

## Notes on Debian packaging

Because I always forget...

* Create initial changelog (needs some manual tweaking afterwards)

	dch --create -v 1.0-0 --package cr-hydra
