# CRHydra - A distributed modeling/inversion framework for CRMod/CRTomo

## Introduction


## Definition of terms

* client: A computer on which a modeling/inversion is requested
* host: A central computer on which the primary database used to control the
  cluster is hosted
* worker: A computer on which the worker program of CRHydra runs, doing actual
  modeling/inversions

## Configuration file

A configuration file is reuqired for cr_hydra to be used, containing
information such as:

* location and access information to database
* Type and location of queue (i.e., directory, or at an later stage the
  database)
* Username (and password)

## Rough outline of functionality

* The client requests a given tomodir/sipdir to be processed by running
  *crh_add* on the corresponding directory
* For each tomodir/sipdir  [IN] (depending on the settings):
	* If a control file [IN].crh is present, assume this directory is being
	  processed at the moment, report it and do nothing (unless directory to)
	* A control file [IN].crh is created with content:
		* datetime of creation, indicating a registration process is in process
	* A unique id is assigned (comprised of user name and random uuid): [ID]
	* The target dir is compressed with the output file comprised of the id and
	  ending tar.gz [ID].tar.gz (alternative compression algorithms can be
	  used)
	* The simulation is registered in the crhydra database and gets assigned a
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

* On the client computer, crh_retrieve or crh_wait_retrieve can be used to
  query the database for finished inversions, which will be transferred back
  and decompressed.
