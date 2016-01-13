#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ("OpenRE - self-learning neural network")
#LONG_DESCRIPTION = open('README.rst').read()
VERSION = '0.0.2'

setup(
    name='openre',
    version=VERSION,
    description=DESCRIPTION,
#    long_description=LONG_DESCRIPTION,
    author='Dmitriy Boyarshinov',
    author_email='dmitriy.boyarshinov@gmail.com',
#    license=open('LICENSE').read(),
    platforms=["any"],
    packages=find_packages(),
    install_requires=[],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
#        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    include_package_data=True,
    scripts=[
        'bin/openre-agent',
        'bin/openre-broker',
        'bin/openre-domain',
        'bin/openre-proxy',
        'bin/openre-server',
        'bin/openrectl'],
    package_data={'': ['license.txt']}
)

