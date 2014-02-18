from setuptools import setup, find_packages
import pyrpm.release as release

setup(name='pyrpm',
      version=release.VERSION,
      description=release.DESCRIPTION,
      long_description=release.LONG_DESCRIPTION,
      author=release.AUTHOR,
      author_email=release.EMAIL,
      maintainer='Dhiru Kholia',
      maintainer_email='dhiru@openwall.com',
      license=release.LICENSE,
      urelease=release.URL,
      classifiers=[
          'Development Status :: 4 - Beta',

          'Topic :: Software Development :: Libraries',
          'License :: OSI Approved :: GPLv2 License',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
      ],
      packages=find_packages(),
      data_files=[],
      zip_safe=False,
      install_requires=[
      ],
      test_suite='tests',
      tests_require=[
          'mock'
      ])
