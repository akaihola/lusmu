from setuptools import setup


setup(name='lusmu',
      version='0.2',
      packages=['lusmu'],
      author='Antti Kaihola',
      author_email='antti.kaihola@eniram.fi',
      description='A lazy/forced evaluation library',
      keywords='eniram reactive lazy evaluation',
      url='https://github.com/akaihola/lusmu',
      test_suite='nose.collector',
      tests_require=['nose==1.3.0'])
