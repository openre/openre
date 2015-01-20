#!/usr/bin/env python

from setuptools import setup, find_packages

DESCRIPTION = ("OpenRE - self-learning neural network")
#LONG_DESCRIPTION = open('README.rst').read()
VERSION = __import__('openre').__version__

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
    install_requires=[
        'numpy==1.7.1',
        'pytest==2.5.2',
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
#        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
)

