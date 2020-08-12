-- inversions

drop table if exists "inversions" cascade;

create table "inversions" (
	index SERIAL PRIMARY KEY,
	username text,
	datetime_init timestamptz,
    archive_file text,
	archive_hash text,
    computer text,
	sim_type text,
    hydra_location text,
    crh_file text,
	ready_for_processing BOOLEAN DEFAULT False
);

