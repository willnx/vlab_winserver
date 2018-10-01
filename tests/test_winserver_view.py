# -*- coding: UTF-8 -*-
"""
A suite of tests for the winserver object
"""
import unittest
from unittest.mock import patch, MagicMock

import ujson
from flask import Flask
from vlab_api_common import flask_common
from vlab_api_common.http_auth import generate_test_token


from vlab_winserver_api.lib.views import winserver


class TestWinServerView(unittest.TestCase):
    """A set of test cases for the WinServerView object"""
    @classmethod
    def setUpClass(cls):
        """Runs once for the whole test suite"""
        cls.token = generate_test_token(username='bob')

    @classmethod
    def setUp(cls):
        """Runs before every test case"""
        app = Flask(__name__)
        winserver.WinServerView.register(app)
        app.config['TESTING'] = True
        cls.app = app.test_client()
        # Mock Celery
        app.celery_app = MagicMock()
        cls.fake_task = MagicMock()
        cls.fake_task.id = 'asdf-asdf-asdf'
        app.celery_app.send_task.return_value = cls.fake_task

    def test_get_task(self):
        """WinServerView - GET on /api/1/inf/winserver returns a task-id"""
        resp = self.app.get('/api/1/inf/winserver',
                            headers={'X-Auth': self.token})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_post_task(self):
        """WinServerView - POST on /api/1/inf/winserver returns a task-id"""
        resp = self.app.post('/api/1/inf/winserver',
                             headers={'X-Auth': self.token},
                             json={'network': "someLAN",
                                   'name': "myWinServerBox",
                                   'image': "someVersion"})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_delete_task(self):
        """WinServerView - DELETE on /api/1/inf/winserver returns a task-id"""
        resp = self.app.delete('/api/1/inf/winserver',
                               headers={'X-Auth': self.token},
                               json={'name' : 'myWinServerBox'})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)

    def test_image(self):
        """WinServerView - GET on the ./image end point returns the a task-id"""
        resp = self.app.get('/api/1/inf/winserver/image',
                            headers={'X-Auth': self.token})

        task_id = resp.json['content']['task-id']
        expected = 'asdf-asdf-asdf'

        self.assertEqual(task_id, expected)


if __name__ == '__main__':
    unittest.main()
