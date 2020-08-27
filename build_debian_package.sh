#!/usr/bin/env sh

test -d dist && rm -r dist
python setup.py sdist
cd dist
tar xvzf cr_hydra*.tar.gz
rm *.tar.gz
cd cr_hydra*
dpkg-buildpackage
