-- we store tomodirs (unfinished and finished) in the database
drop table if exists "binary_data" cascade;

create table "binary_data" (
	index SERIAL PRIMARY KEY,
	filename text,
	hash text,
	bytea data
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
	status text default 'unfinished'
);
