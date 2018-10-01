#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
winserver RESTful API
"""
from setuptools import setup, find_packages


setup(name="vlab-winserver-api",
      author="Nicholas Willhite,",
      author_email='willnx84@gmail.com',
      version='0.0.1',
      packages=find_packages(),
      include_package_data=True,
      package_files={'vlab_winserver_api' : ['app.ini']},
      description="winserver",
      install_requires=['flask', 'ldap3', 'pyjwt', 'uwsgi', 'vlab-api-common',
                        'ujson', 'cryptography', 'vlab-inf-common', 'celery']
      )
