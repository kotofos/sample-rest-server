# todo integration tests
import unittest
import client
import json
from client import AsyncTaskClient
from httmock import HTTMock


class TestClient(unittest.TestCase):

    def setUp(self):
        self.client = AsyncTaskClient()

        def nop(arg):
            pass
        client._output_response = nop

    def test_get_result_none(self):
        def my_mock(url, request):
            return json.dumps({'task': {'result': None}})

        with HTTMock(my_mock):
            result = self.client.get_result(1)
        assert result is None

    def test_get_result_not_none(self):
        def my_mock(url, request):
            return json.dumps({'task': {'result': '123'}})

        with HTTMock(my_mock):
            result = self.client.get_result(1)
        assert result == '123'

    def test_get_status_not_none(self):
        def my_mock(url, request):
            return json.dumps({'task': {'status': 'done'}})

        with HTTMock(my_mock):
            result = self.client.get_status(1)
        assert result

    def test_get_task_create(self):
        def my_mock(url, request):
            return json.dumps({'task': {'id': 1}})

        with HTTMock(my_mock):
            result = self.client.create_task('a', 'b')
        assert result == 1

    # todo timeout
    def test_wait_for_task(self):
        client = AsyncTaskClient(batch_mode=True)

        def create_mock(url, request):
            return json.dumps({'task': {'id': 1}})

        def wait_mock(url, request):
            if 'status' in url.path:
                return json.dumps(
                    {'task': {'id': 1, 'status': 'done', }})
            elif 'result' in url.path:
                return json.dumps(
                    {'task': {'id': 1, 'result': 'a'}})

        with HTTMock(create_mock):
            tid = client.create_task('a', 'b')

        with HTTMock(wait_mock):
            client.wait_for_result(tid)
