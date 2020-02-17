import sys
import os
import uuid
import psutil
import subprocess
from flask import request, jsonify, Response
from flask import Blueprint, redirect, url_for

from args import get_cli
from config import JOB_FOLDER

FILENAME_LOG = os.path.join(JOB_FOLDER, '{}.log')
FILENAME_PID = os.path.join(JOB_FOLDER, '{}.pid')

SEP = '=-' * 30

app_with_subprocess = Blueprint('app_with_subprocess ', __name__,
                                template_folder='templates')


@app_with_subprocess.route('/run/<command>', methods=['POST'])
def run_post(command):
    params = request.get_json()
    found, cli = get_cli(command)
    if not found:
        return redirect(url_for('list_available_commands'))

    args = cli.parser.parse_args(params)
    code = 'from {module} import {function}; import argparse; args = argparse.Namespace(**{args}); r = ({function}(args)); print(\'{SEP}\'); print(r)'.format(
        module=cli.function.__module__,
        function=cli.function.__name__,
        SEP=SEP,
        args=args.__dict__
    )

    task_id = str(uuid.uuid4())

    f = open(FILENAME_LOG.format(task_id), 'w+')

    p = subprocess.Popen([sys.executable, '-u', '-c', code], stderr=f, stdout=f, bufsize=0)
    with open(FILENAME_PID.format(task_id), 'w') as ff:
        ff.write(str(p.pid))
    return str(task_id)


@app_with_subprocess.route('/status/<task_id>')
def task_status(task_id):

    try:
        with open(FILENAME_PID.format(task_id), 'r') as f:
            pid = int(f.read())
        process = psutil.Process(pid)
    except (FileNotFoundError, psutil.NoSuchProcess, psutil.AccessDenied):
        process = None

    fname = FILENAME_LOG.format(task_id)

    if request.headers.get('accept') == 'text/event-stream':
        def status():
            while process is not None:
                try:
                    process_running = process.status() == psutil.STATUS_RUNNING
                except psutil.NoSuchProcess:
                    process_running = False
                if not process_running:
                    break
                try:
                    with open(fname, 'r') as f:
                        resp = ["data: {}".format(line.strip()) for line in f.readlines()]
                except (FileNotFoundError, IOError):
                    resp = ['data: \n']

                resp.append('\n')

                yield '\n'.join(resp)
            yield 'data: \n\n'
        return Response(status(), content_type='text/event-stream')

    try:
        with open(fname, 'r') as f:
            lines = f.readlines()
            i = len(lines) - 1
            while i >= 0:

                if lines[i].strip() == SEP:
                    break
                i -= 1
            if len(lines) > 0 and i >= 0:
                resp = '\n'.join([line.strip() for line in lines[i + 1:]])
            else:
                resp = ''
    except (FileNotFoundError, IOError):
        resp = ''

    return jsonify(resp)



