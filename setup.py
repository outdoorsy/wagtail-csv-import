#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='wagtail-csv-import',
    version='0.3.1',
    description="Page import from CSV file",
    author='Outdoorsy.com',
    author_email='joe@outdoorsy.com',
    url='https://github.com/outdoorsy/wagtail-csv-import',
    packages=find_packages(exclude=['tests*']),
    include_package_data=True,
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
    ],
)
