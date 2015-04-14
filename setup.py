#!/usr/bin/env python3.4

from setuptools import setup, find_packages

setup(name='MangaDL',
      version='0.1.0',
      description='A general purpose Manga scraping utility',
      keywords='manga scraper',
      url='https://github.com/FujiMakoto/MangaDL',
      license='MIT',

      author='Makoto Fujikawa',
      maintainer='Makoto Fujikawa',
      author_email='makoto@makoto.io',

      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'manga-dl = src.manga_dl:main',
          ]
      },

      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: MIT License',
          'Natural Language :: English',
          'Programming Language :: Python :: 3.4',
          'Topic :: Internet :: WWW/HTTP :: Indexing/Search'
      ],

      install_requires=[
          'requests>=2.6',
          'img2pdf>=0.1.5',
          'clint>=0.4.1',
          'appdirs>=1.4',
          'progressbar33>=2.4'
      ],
      )