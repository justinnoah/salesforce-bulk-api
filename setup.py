# encoding: utf-8
#
# Copyright (c) 2015 Safari Books Online. All rights reserved.
#
# This software may be modified and distributed under the terms
# of the 3-clause BSD license.  See the LICENSE file for details.

from __future__ import unicode_literals, with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

VERSION = '1.0.1'

setup(
    name='salesforce_bulk_api',
    version=VERSION,
    author='Chris Guidry',
    author_email='cguidry@safaribooksonline.com',
    url='https://github.com/safarijv/salesforce-bulk-api',
    py_modules=['salesforce_bulk_api'],
    description='A Python 2 and 3 interface to the Salesforce Bulk API.',
    license='BSD',
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Office/Business :: Groupware',
        'Topic :: Software Development :: Libraries',
        'Topic :: Utilities'
    ],
    install_requires=[
        'requests>=2.5.3',
        'simple_salesforce>=0.68.0'
    ]
)
