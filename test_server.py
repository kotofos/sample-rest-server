import unittest
import app
from app import TasksProcessor


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

    def test_task_mix_even_even(self):
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


