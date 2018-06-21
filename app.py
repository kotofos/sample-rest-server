import json
import re
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler

from flask import Flask, jsonify
from flask import abort
from flask import request

API_VERSION = '1.0'
API_URL = f'/api/v{API_VERSION}/tasks'

TASKS_QUEUE_POLL_TIME_S = 0.1

run_thread = True
app = Flask(__name__)


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
        'payload': 'Buy groceries',
        'type': 'reverse',
        'status': 'done',
        'result': 'seircg yub',
    },
]

tasks_queue = deque()


class RestHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not self.path.startswith(API_URL):
            self.abort_not_found()
            return

        sub_path = self.path.replace(API_URL, '', 1)
        if sub_path == '' or sub_path == '/':
            self.send_json_data({'tasks': tasks})
            return

        task_status_pattern = re.compile('/([0-9]+)/status[/]?')
        task_result_pattern = re.compile('/([0-9]+)/result[/]?')

        task_id_status = task_status_pattern.search(sub_path)
        if task_id_status:
            self.get_task_status(task_id_status)
            return

        task_id_result = task_result_pattern.search(sub_path)
        if task_id_result:
            self.get_task_result(task_id_result)
            return

        self.abort_not_found()

    def _get_task(self, task_id_match):
        task_id = int(task_id_match.group(1))
        task = list(filter(lambda t: t['id'] == task_id, tasks))
        if len(task) == 0:
            self.abort_not_found()
            return None
        return task[0]

    def get_task_status(self, task_id_match):
        task = self._get_task(task_id_match)
        if not task:
            return
        self.send_json_data(
            {'task': {'id': task['id'], 'status': task['status']}})

    def get_task_result(self, task_id_match):
        task = self._get_task(task_id_match)
        if not task:
            return
        if task['result'] is None:
            self.abort_not_found()
        self.send_json_data(
            {'task': {'id': task['id'], 'result': task['result']}})

    def do_POST(self):
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
            self.abort_bad_request()
            return

        tasks.append(task)
        tasks_queue.appendleft(task)

        self.send_json_data({'task': task}, status=HTTPStatus.CREATED)
        return

    def send_end_response(self, code):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def abort_not_found(self):
        self.send_end_response(HTTPStatus.NOT_FOUND)
        self.send_json_data({'error': 'Not found'}, HTTPStatus.NOT_FOUND)

    def abort_bad_request(self):
        self.send_end_response(HTTPStatus.BAD_REQUEST)
        self.send_json_data({'error': 'Bad request'}, HTTPStatus.NOT_FOUND)

    def send_json_data(self, data, status=HTTPStatus.OK):
        self.send_end_response(status)
        self.wfile.write(json.dumps(data).encode())


def create_task():
    if not request.json or 'payload' not in request.json:
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'payload': request.json['payload'],
        'type': request.json.get('type', ''),
        'status': TaskStatus.queued,
        'result': None,
    }
    tasks.append(task)
    tasks_queue.appendleft(task)
    return jsonify({'task': task}), 201


def handle_tasks():
    while run_thread:
        try:
            task = tasks_queue.pop()
        except IndexError:
            time.sleep(TASKS_QUEUE_POLL_TIME_S)
            continue
            # todo or use cond var/event

        process_task(task)


def process_task(task):
    task['status'] = TaskStatus.running

    if task['type'] == TaskType.reverse:
        time.sleep(TaskType.reverse_time)
        task['result'] = reverse_string(task['payload'])

    elif task['type'] == TaskType.mix_even:
        time.sleep(TaskType.mix_even_time)
        task['result'] = mix_even((task['payload']))

    else:
        task['status'] = TaskStatus.error
        return

    task['status'] = TaskStatus.done


def reverse_string(data):
    return data[::-1]


def mix_even(data):
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


if __name__ == '__main__':
    t_ = threading.Thread(target=handle_tasks)
    t_.daemon = True
    t_.start()

    httpd = HTTPServer(('0.0.0.0', 8000), RestHTTPRequestHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

    run_thread = False
    t_.join()
