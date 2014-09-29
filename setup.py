"""Lusmu setup information

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""


from setuptools import setup


setup(name='lusmu',
      version='0.2.3',
      packages=['lusmu'],
      author='Antti Kaihola',
      author_email='antti.kaihola@eniram.fi',
      license='BSD',
      description='A dataflow/reactive programming library for Python',
      keywords='eniram dataflow reactive',
      url='https://github.com/akaihola/lusmu',
      test_suite='nose.collector',
      tests_require=['mock==1.0.1', 'nose==1.3.0'])
