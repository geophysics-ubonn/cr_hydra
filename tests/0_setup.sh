#!/usr/bin/env sh
outdir="test00"
test -d "${outdir}" && rm -r "${outdir}"
mkdir "${outdir}"

cp -r "unfinished_inversions/20_157.142860" "${outdir}/"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/01"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/02"
