#!/usr/bin/env sh
outdir="test00"
test -d "${outdir}" && rm -r "${outdir}"
mkdir "${outdir}"

cp -r "unfinished_inversions/20_157.142860" "${outdir}/"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/01"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/02"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/03"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/04"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/05"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/06"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/07"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/08"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/09"

cd "${outdir}"
crh_add
crh_worker
