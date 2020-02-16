import os
import logging
import contextlib
import dill
import binascii
from flask import request, jsonify, Response
from flask import Blueprint, redirect, url_for
from celery import Celery
from args import get_cli
from config import JOB_FOLDER, CELERY_BROKER_URL, RESULT_BACKEND


celery = Celery('argparser_server', broker=CELERY_BROKER_URL, backend=RESULT_BACKEND)

FILENAME_LOG = os.path.join(JOB_FOLDER, '{}.log')

app_with_celery = Blueprint('app_with_celery', __name__,
                            template_folder='templates')


@celery.task(name='server.background_task', bind=True)
def background_task(self, function, args):
    logger = logging.getLogger(self.request.id)
    filehandler = logging.FileHandler(FILENAME_LOG.format(self.request.id))
    logger.addHandler(filehandler)

    function = dill.loads(binascii.a2b_base64(function))
    args = dill.loads(binascii.a2b_base64(args))

    with contextlib.redirect_stdout(LoggerWriter(logger, 20)):
        return function(args)


@app_with_celery.route('/run/<command>', methods=['POST'])
def run_post(command):
    params = request.get_json()
    found, cli = get_cli(command)
    if not found:
        return redirect (url_for('list_available_commands'))
    func = binascii.b2a_base64(dill.dumps(cli.function)).decode()
    args = cli.parser.parse_args(params)
    base64_args = binascii.b2a_base64(dill.dumps(args)).decode()
    task = background_task.apply_async(args=(func, base64_args))
    return task.id


@app_with_celery.route('/status/<task_id>')
def task_status(task_id):
    task = background_task.AsyncResult(task_id)
    if request.headers.get('accept') == 'text/event-stream':
        def status():
            while task.status not in ('SUCCESS', 'FAILURE', 'REVOKED'):
                fname = FILENAME_LOG.format(task_id)
                resp = ['data: \n']
                if os.path.isfile(fname):
                    with open(fname, 'r') as f:
                        resp = ["data: {}".format(line.strip()) for line in f.readlines()]
                resp.append('\n')

                yield '\n'.join(resp)
            yield "data: \n\n"
        return Response(status(), content_type='text/event-stream')
    if task.status == 'SUCCESS':
        return jsonify(task.result)
    return jsonify(task.status)


class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)

    def flush(self, *kargs, **kwargs):
        pass
