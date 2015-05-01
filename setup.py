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
        'Jinja2==2.7.3',
        'MarkupSafe==0.23',
        'appdirs==1.4.0',
        'argparse==1.2.1',
        'decorator==3.4.0',
        'distribute==0.6.24',
        'docutils==0.12',
        'lockfile==0.10.2',
        'numpy==1.7.1',
        'py==1.4.26',
        'pyopencl==2014.1',
        'pytest==2.6.4',
        'python-daemon==2.0.5',
        'pytools==2014.3.5',
        'pyzmq==14.6.0',
        'six==1.9.0',
        'wsgiref==0.1.2',
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

