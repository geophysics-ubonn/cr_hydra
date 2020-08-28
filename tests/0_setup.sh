#!/usr/bin/env sh
outdir="test00"
test -d "${outdir}" && rm -r "${outdir}"
mkdir "${outdir}"

cp -r "unfinished_inversions/20_157.142860" "${outdir}/"
cp -r "unfinished_inversions/20_157.142860" "${outdir}/01"
overwrite to make the inversion fail with an error.dat file
echo 0 >  "${outdir}/01/grid/elem.dat"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/02"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/03"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/04"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/05"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/06"
# mkdir "${outdir}"/subdir1
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/subdir1/07"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/08"
# cp -r "unfinished_inversions/20_157.142860" "${outdir}/09"

# # forward modelings
# cp -r "unfinished_modelings/mod1" "${outdir}/mod01"

cd "${outdir}"
crh_add
crh_worker --quit
