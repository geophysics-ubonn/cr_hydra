#!/usr/bin/env bash
outdir="test01"
test -d "${outdir}" && rm -r "${outdir}"
mkdir "${outdir}"

for i in {1..30}
do
	cp -r "unfinished_inversions/td_large" "${outdir}/td_${i}"

done

cd "${outdir}"
crh_add
# crh_worker --quit
