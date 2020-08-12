#!/usr/bin/env python
from setuptools import setup, find_packages

version_long = '0.1.0-dev0'


if __name__ == '__main__':
    setup(
        name='cr_hydra',
        version=version_long,
        description='CRHydra - distributed CRTomo computing',
        author='Maximilian Weigand',
        author_email='mweigand@geo.uni-bonn.de',
        license='MIT',
        # url='https://github.com/geophysics-ubonn/reda',
        packages=find_packages("lib"),
        package_dir={'': 'lib'},
        # install_requires=['numpy', 'scipy', 'pandas', 'matplotlib'],
    )
