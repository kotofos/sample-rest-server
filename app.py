import json
import re
import threading
import time
import logging
from argparse import ArgumentParser
from collections import deque
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADDRESS = '0.0.0.0'
PORT = 8000

API_VERSION = '1.0'
API_URL = f'/api/v{API_VERSION}/tasks'

TASKS_POLL_PERIOD_S = 0.1

run_thread = True
cond_new_task = threading.Condition()
tasks_queue = deque()


class TaskStatus:
    queued = 'queued'
    running = 'running'
    done = 'done'
    error = 'error'


class TaskType:
    reverse = 'reverse'
    reverse_time = 3
    mix_even = 'mix_even'
    mix_even_time = 7


tasks = [
    {
        'id': 1,
        'payload': 'sample task',
        'type': 'reverse',
        'status': 'done',
        'result': 'sample task',
    },
]


class RestJsonHTTPRequestHandler(BaseHTTPRequestHandler):
    task_status_pattern = re.compile('/([0-9]+)/status[/]?')
    task_result_pattern = re.compile('/([0-9]+)/result[/]?')

    def get_tasks_list(self):
        self._send_json_data({'tasks': tasks})

    def get_task_status(self, task_id_match):
        task = self._get_task(task_id_match)
        if not task:
            return
        self._send_json_data(
            {'task': {'id': task['id'], 'status': task['status']}})

    def get_task_result(self, task_id_match):
        task = self._get_task(task_id_match)
        if not task:
            return
        if task['result'] is None:
            self._abort_not_found()
        self._send_json_data(
            {'task': {'id': task['id'], 'result': task['result']}})

    def post_task(self):
        data_string = self.rfile.read(
            int(self.headers['Content-Length'])).decode()

        data = json.loads(data_string)
        try:
            task = {
                'id': tasks[-1]['id'] + 1,
                'payload': data['payload'],
                'type': data['type'],
                'status': TaskStatus.queued,
                'result': None,
            }
        except KeyError:
            self._abort_bad_request()
            return

        tasks.append(task)
        tasks_queue.appendleft(task)
        with cond_new_task:
            cond_new_task.notify_all()

        self._send_json_data({'task': task}, status=HTTPStatus.CREATED)

    def do_GET(self):
        if not self.path.startswith(API_URL):
            self._abort_not_found()
            return

        sub_path = self.path.replace(API_URL, '', 1)
        if sub_path == '' or sub_path == '/':
            self.get_tasks_list()
            return

        task_id_status = self.task_status_pattern.search(sub_path)
        if task_id_status:
            self.get_task_status(task_id_status)
            return

        task_id_result = self.task_result_pattern.search(sub_path)
        if task_id_result:
            self.get_task_result(task_id_result)
            return

        self._abort_not_found()

    def do_POST(self):
        self.post_task()

    def _get_task(self, task_id_match):
        task_id = int(task_id_match.group(1))
        task = list(filter(lambda t: t['id'] == task_id, tasks))
        if len(task) == 0:
            self._abort_not_found()
            return None
        return task[0]

    def _send_end_response(self, code):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def _abort_not_found(self):
        self._send_json_data({'error': 'Not found'}, HTTPStatus.NOT_FOUND)

    def _abort_bad_request(self):
        self._send_end_response(HTTPStatus.BAD_REQUEST)
        self._send_json_data({'error': 'Bad request'}, HTTPStatus.NOT_FOUND)

    def _send_json_data(self, data, status=HTTPStatus.OK):
        self._send_end_response(status)
        self.wfile.write(json.dumps(data).encode())


def handle_tasks():
    processor = TasksProcessor(TASKS_POLL_PERIOD_S)
    while run_thread:
        while run_thread:
            processor.process_queue()


class TasksProcessor:
    def __init__(self, poll_time_s):
        self.poll_time_s = poll_time_s

    def process_queue(self):
        with cond_new_task:
            cond_new_task.wait(self.poll_time_s)
            if not tasks_queue:
                return
            task = tasks_queue.pop()
        self.process_task(task)

    def process_task(self, task):
        task['status'] = TaskStatus.running
        logging.info(f'Processing task {task["id"]}')

        if task['type'] == TaskType.reverse:
            time.sleep(TaskType.reverse_time)
            task['result'] = self.reverse_string(task['payload'])

        elif task['type'] == TaskType.mix_even:
            time.sleep(TaskType.mix_even_time)
            task['result'] = self.mix_even((task['payload']))

        else:
            task['status'] = TaskStatus.error
            return

        task['status'] = TaskStatus.done
        logging.info(f'Task {task["id"]} processed')

    def reverse_string(self, data):
        return data[::-1]

    def mix_even(self, data):
        mixed = []
        i = 0
        while i < len(data):
            if i == len(data) - 1:
                mixed.append(data[i])
                break
            mixed.append(data[i + 1])
            mixed.append(data[i])
            i += 2
        return ''.join(mixed)


class App:
    def __init__(self, addr, port):
        self.address = addr
        self.port = port

    def run(self):
        t = self.start_thread()
        self.run_server()
        self.stop_thread(t)

    def start_thread(self):
        t = threading.Thread(target=handle_tasks)
        t.daemon = True
        t.start()
        logger.info('Task queue started')
        return t

    def stop_thread(self, t):
        global run_thread
        run_thread = False
        with cond_new_task:
            cond_new_task.notify_all()
        t.join()
        logger.info('Task queue stopped')

    def run_server(self):
        httpd = HTTPServer((self.address, self.port),
                           RestJsonHTTPRequestHandler)
        try:
            logger.info('Server started')
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        logger.info('Server stopped')


if __name__ == '__main__':
    parser = ArgumentParser('HTTP REST-JSON API server')
    parser.add_argument('ip', default=ADDRESS, nargs='?',
                        help='ip of server')
    parser.add_argument('port', default=PORT, type=int, nargs='?',
                        help='port of server')
    args = parser.parse_args()

    app = App(args.ip, args.port)
    app.run()
