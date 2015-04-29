"""Lusmu setup information

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

import os
from setuptools import setup


here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()


setup(name='lusmu',
      version='0.2.4.dev',
      packages=['lusmu'],
      author='Antti Kaihola',
      author_email='antti.kaihola@eniram.fi',
      license='BSD',
      description='A dataflow/reactive programming library for Python',
      long_description=README,
      keywords='eniram dataflow reactive',
      url='https://github.com/akaihola/lusmu',
      test_suite='nose.collector',
      tests_require=['mock==1.0.1', 'nose==1.3.0'])
