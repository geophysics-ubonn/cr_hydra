-- we store tomodirs (unfinished and finished) in the database
drop table if exists "binary_data" cascade;

create table "binary_data" (
	index SERIAL PRIMARY KEY,
	filename text,
	hash text,
	data bytea
);

-- inversions
drop table if exists "inversions" cascade;

create table "inversions" (
	index SERIAL PRIMARY KEY,
	--
	username text,
	datetime_init timestamptz,
    tomodir_unfinished_file integer references binary_data (index),
    tomodir_finished_file integer references binary_data (index),
    source_computer text,
	-- mod or inv
	sim_type text,
    -- hydra_location text,
	-- path to crh meta data file (replaces the actual tomodir) on
	-- source_computer
    crh_file text,
	-- everything is uploaded
	ready_for_processing BOOLEAN DEFAULT False,
	-- set to "finished" when inversion is ready
	status text default 'unfinished',
	inv_computer text,
	datetime_inversion_started timestamptz,
	datetime_finished timestamptz,
	downloaded BOOLEAN DEFAULT False
);

-- per node settings
-- each computer will need certain settings, such as number of cpus to use,
-- nice level, etc.
drop table if exists "node_settings" cascade;

create table "node_settings" (
	index serial PRIMARY key,
	node_name text unique,
	-- with which nice level should inversions be run?
	nice_level integer default 20,
	-- note that the total number of CRTomo instances (and thus workers) used
	-- computes to:
	-- nr_cpus / nr_threads
	nr_cpus integer default 2,
	nr_threads integer default 2
);
