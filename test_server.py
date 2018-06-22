import unittest
import app
from app import TasksProcessor
from io import BytesIO as IO


class TestTaskProcessor(unittest.TestCase):
    def setUp(self):
        app.tasks_queue.clear()

    def test_no_tasks_ok(self):
        t = TasksProcessor(0)
        t.process_queue()

    def test_task_reverse(self):
        app.TaskType.reverse_time = 0
        task = {
            'id': 1,
            'type': app.TaskType.reverse,
            'payload': '123',
        }
        app.tasks_queue.append(task)
        t = TasksProcessor(0)
        t.process_queue()
        assert len(app.tasks_queue) == 0
        assert task['result'] == '321'

    def test_task_mix_even_even(self):
        app.TaskType.mix_even_time = 0
        task = {
            'id': 1,
            'type': app.TaskType.mix_even,
            'payload': '1234',
            'status': app.TaskStatus.queued
        }
        app.tasks_queue.append(task)
        t = TasksProcessor(0)
        t.process_queue()
        assert task['status'] == app.TaskStatus.done
        assert len(app.tasks_queue) == 0
        assert task['result'] == '2143'

    def test_task_mix_even_odd(self):
        app.TaskType.mix_even_time = 0
        task = {
            'id': 1,
            'type': app.TaskType.mix_even,
            'payload': '123',
        }
        app.tasks_queue.append(task)
        t = TasksProcessor(0)
        t.process_queue()
        assert task['result'] == '213'

    def test_task_bad(self):
        task = {
            'id': 1,
            'type': 'none',
            'payload': '123',
        }
        app.tasks_queue.append(task)
        t = TasksProcessor(0)
        t.process_queue()
        assert task['status'] == app.TaskStatus.error
        assert 'result' not in task


class MockRequest:
    def __init__(self, request_data):
        self.data = request_data

    def makefile(self, *args, **kwargs):
        return IO(self.data)

    def sendall(self, b):
        pass


class MockServer:
    def __init__(self, ip_port, Handler, data):
        handler = Handler(MockRequest(data), ip_port, self)


# todo use mock instead
class TestHTTPHandler(app.RestJsonHTTPRequestHandler):
    def log_message(self, format_, *args):
        global output_msg
        output_msg = args


class TestServerNoExceptions(unittest.TestCase):
    def setUp(self):
        global output_msg
        output_msg = (None, None)

    def send_request(self, data):
        MockServer(('0.0.0.0', 8888), TestHTTPHandler,
                   data.encode())

    def test_get(self):
        self.send_request('GET /')
        assert output_msg[1] == '404'

    def test_get_bad_url(self):
        self.send_request(f'GET {app.API_URL}/random')
        assert output_msg[1] == '404'

    def test_list_tasks(self):
        self.send_request(f'GET {app.API_URL}')
        assert output_msg[1] == '200'

    def test_get_task_status(self):
        self.send_request(f'GET {app.API_URL}/1/status/')
        assert output_msg[1] == '200'

    def test_get_task_result(self):
        self.send_request(f'GET {app.API_URL}/1/result/')
        assert output_msg[1] == '200'

    def test_put(self):
        self.send_request(f'PUT {app.API_URL}')
        assert output_msg[1] == '400'
