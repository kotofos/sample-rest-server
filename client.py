# todo docstring
# todo type hints
# todo logging
# todo config file support

import signal
import sys
import time
import requests
import argparse

ADDRESS = '0.0.0.0'
PORT = 8000

API_VERSION = '1.0'
API_PATH = f'/api/v{API_VERSION}/tasks'

abort = False


def signal_handler(signal, frame):
    global abort
    abort = True


signal.signal(signal.SIGINT, signal_handler)


class AsyncTaskClient:
    def __init__(self, batch_mode=False, address=ADDRESS, port=PORT):
        self.batch_mode = batch_mode
        self.task_id = None
        self.api_url = f'http://{address}:{port}{API_PATH}'

    def create_task(self, type_, payload):
        data = {
            'type': type_,
            'payload': payload,
        }
        r = requests.post(self._url(), json=data)
        r.raise_for_status()
        _output_response(r.text)
        data = r.json()

        tid = data['task']['id']
        self.task_id = tid

        if not self.batch_mode:
            _output_response(data)
        else:
            _output_response(f'task id {tid}')
        return tid

    def wait_for_result(self, task_id):
        while not abort:
            status = self.get_status(task_id)
            if status:
                break
            time.sleep(1)
        else:
            _output_response('aborted')
            sys.exit(0)

        self.get_result(self.task_id)

    def get_status(self, task_id):
        r = requests.get(self._url(f'/{task_id}/status'))
        r.raise_for_status()
        data = r.json()
        if not self.batch_mode:
            _output_response(data)
        else:
            _output_response(data['task']['status'])

        return data['task']['status'] == 'done'

    def get_result(self, task_id):
        r = requests.get(self._url(f'/{task_id}/result'))
        r.raise_for_status()
        data = r.json()
        _output_response(data)
        return data['task']['result']

    def _url(self, suffix=''):
        return ''.join((self.api_url, suffix))


def _output_response(msg):
    # todo alternative output methods
    print(msg)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Async task api client')
    parser.add_argument('ip', default=ADDRESS, nargs='?',
                        help='ip of server')
    parser.add_argument('port', default=PORT, type=int, nargs='?',
                        help='port of server')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-c', '--create', metavar=('TYPE', 'PAYLOAD'), nargs=2,
                       help='create task')
    parser.add_argument('-w', '--wait', action='store_const', const=True,
                        help='wait for task to finish')
    group.add_argument('-s', '--status', type=int, metavar='ID',
                       help='get task status')
    group.add_argument('-r', '--result', type=int, metavar='ID',
                       help='get task result')

    args = parser.parse_args()

    if args.create is None and args.wait is not None:
        parser.error('--wait can only be set for --create')

    client = AsyncTaskClient(args.wait, args.ip, args.port)

    try:
        if args.create is not None:
            tid = client.create_task(*args.create)
            if args.wait:
                client.wait_for_result(tid)

        elif args.status is not None:
            client.get_status(args.status)

        elif args.result is not None:
            client.get_result(args.result)
    except requests.exceptions.HTTPError as e:
        _output_response(e)
