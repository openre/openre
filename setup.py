#!/usr/bin/env python

from setuptools import setup
import os.path

DESCRIPTION = "OpenRE - self-learning neural network"
LONG_DESCRIPTION = open('README.md').read()
version_file = open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'VERSION'))
VERSION = version_file.read().strip()

setup(
    name='openre',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    author='Dmitriy Boyarshinov',
    author_email='dmitriy.boyarshinov@gmail.com',
    license=open('LICENSE').read(),
    platforms=["any"],
    packages=['openre'],
    url = 'https://github.com/openre/openre',
    download_url = 'https://github.com/openre/openre/tarball/%s' % VERSION,
    install_requires=[
        'Jinja2==3.1.3',
        'MarkupSafe==0.23',
        'appdirs==1.4.0',
        'argparse==1.2.1',
        'decorator==3.4.0',
        'docutils==0.12',
        'lockfile==0.10.2',
        'numpy==1.22.0',
        'py==1.10.0',
        'pyopencl==2014.1',
        'pytest==2.6.4',
        'python-daemon==2.0.5',
        'pytools==2014.3.5',
        'pyzmq==15.4.0',
        'six==1.9.0',
        'wsgiref==0.1.2',
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    include_package_data=True,
    scripts=[
        'openre/bin/openre-agent',
        'openre/bin/openre-broker',
        'openre/bin/openre-domain',
        'openre/bin/openre-proxy',
        'openre/bin/openre-server',
        'openre/bin/openrectl'],
)

