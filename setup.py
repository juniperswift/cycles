#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))

setup(name='cycles',
      version='1.0',
      description='a command line utility for logging menstrual cycles',
      install_requires={'python-dateutil>=2.1',},
      entry_points={
            'console_scripts': [
                'cycles = cycles:cli',
            ],
        },
      author='jmjordan',
      url='http://github.com/jmjordan/cycles',
      packages=['libcycles'],
      py_modules=['cycles'],
     )