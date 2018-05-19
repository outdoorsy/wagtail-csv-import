#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='wagtail-csv-import',
    version='0.1',
    description="Page import from CSV file",
    author='Outdoorsy.com',
    author_email='joe@outdoorsy.com',
    url='https://github.com/outdoorsy/wagtail-csv-import',
    packages=find_packages(),
    include_package_data=True,
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
    ],
)
