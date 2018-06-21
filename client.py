# todo unit tests
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
API_URL = f'http://{ADDRESS}:{PORT}/api/v1.0/tasks'

abort = False


def signal_handler(signal, frame):
    global abort
    abort = True


signal.signal(signal.SIGINT, signal_handler)


class AsyncTaskClient:
    def __init__(self, batch_mode):
        self.batch_mode = batch_mode
        self.task_id = None

    def create_task(self, type_, payload):
        data = {
            'type': type_,
            'payload': payload,
        }
        r = requests.post(API_URL, json=data)
        r.raise_for_status()
        print(r.text)
        data = r.json()

        tid = data['task']['id']
        self.task_id = tid

        if not self.batch_mode:
            self._output_responce(data)
        else:
            self._output_responce(f'task id {tid}')
        return tid

    def wait_for_result(self):
        while not abort:
            status = self.get_status(self.task_id)
            if status:
                break
            time.sleep(1)
        else:
            self._output_responce('aborted')
            sys.exit(0)

        self.get_result(self.task_id)

    def get_status(self, task_id):
        r = requests.get(API_URL + f'/{task_id}/status')
        r.raise_for_status()
        data = r.json()
        if not self.batch_mode:
            self._output_responce(data)
        else:
            self._output_responce(data['task']['status'])

        return data['task']['status'] == 'done'

    def get_result(self, task_id):
        r = requests.get(API_URL + f'/{task_id}/result')
        r.raise_for_status()
        data = r.json()
        self._output_responce(data)
        return data['task']['result']

    def _output_responce(self, *args, **kwargs):
        # todo alternative output methods
        print(*args, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Async task api client')
    parser.add_argument('-c', '--create', metavar=('TYPE', 'PAYLOAD'), nargs=2,
                        help='create task')
    parser.add_argument('-w', '--wait', action='store_const', const=True,
                        help='wait for task to finish')
    parser.add_argument('-s', '--status', type=int, metavar='ID',
                        help='get task status')
    parser.add_argument('-r', '--result', type=int, metavar='ID',
                        help='get task result')

    args = parser.parse_args()

    client = AsyncTaskClient(args.wait)

    # todo do not mix args
    if args.create is not None:
        client.create_task(*args.create)
        if args.wait:
            client.wait_for_result()

    elif args.status is not None:
        client.get_status(args.status)

    elif args.result is not None:
        client.get_result(args.result)
