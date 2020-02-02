import os
import io
import sys
import contextlib
from collections import OrderedDict
import logging
import binascii
import importlib
import socket
import dill
from celery import Celery
from flask import Flask, request, Response, jsonify
import jinja2

import args
from argparse2dict import argparser_to_dict


app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['result_backend'] = 'redis://localhost:6379/0'
app.config['task_track_started'] = True
app.config['worker_redirect_stdouts'] = False
app.config['worker_hijack_root_logger'] = False

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], backend=app.config['result_backend'])
celery.conf.update(app.config)


TEMPLATE_FOLDER = './templates'
TEMPLATE_FILE = "default_template.html"

SERVER_NAME = socket.gethostbyname(socket.gethostname())
SERVER_PORT = 5000

template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_FOLDER)
template_env = jinja2.Environment(loader=template_loader)


def get_cli(cmd):
    cmds = [parser for parser in args.parsers if parser.name == cmd]

    if len(cmds) == 0:
        return False, list_available_commands()
    if len(cmds) > 1:
        return False, (500, "more than one parser with prog name '{}' found ".format(cmd))
    cli = cmds[0]
    return True, cli


@app.route('/')
def show_command_line_options():
    cmd = request.args.get('command')

    found, cli = get_cli(cmd)
    if not found:
        return cli
    parser = cli.parser

    if os.path.isfile(os.path.join(TEMPLATE_FOLDER, '{}.html'.format(cmd))):
        template_file = '{}.html'.format(cmd)
    else:
        template_file = TEMPLATE_FILE
    template = template_env.get_template(template_file)
    server = 'http://{}:{}/run/{}'.format(SERVER_NAME, SERVER_PORT, cmd)

    return template.render(title=cli.name,
                           description=cli.parser.description,
                           args=argparser_to_dict(parser),
                           server=server)


@app.route('/list')
def list_available_commands():
    template = template_env.get_template('list_commands.html')
    cmds = {parser.name: 'http://{}:{}/?command={}'.format(SERVER_NAME, SERVER_PORT,
                                                           parser.name) for parser in args.parsers}
    cmds_sorted = OrderedDict()
    for cmd in sorted(cmds.keys()):
        cmds_sorted[cmd] = cmds[cmd]

    return template.render(args=cmds_sorted)


@app.route('/refresh')
def refresh():
    importlib.reload(args)
    return 'refreshed argparsers'


@app.route('/run/<command>', methods=['POST'])
def run_post(command):
    params = request.get_json()
    found, cli = get_cli(command)
    if not found:
        return cli
    func = binascii.b2a_base64(dill.dumps(cli.function)).decode()
    args = cli.parser.parse_args(params)
    args = binascii.b2a_base64(dill.dumps(args)).decode()
    task = background_task.apply_async(args=(func, args))
    return task.id


@app.route('/status/<task_id>')
def task_status(task_id):
    task = background_task.AsyncResult(task_id)
    if request.headers.get('accept') == 'text/event-stream':
        def status():
            sys.stdout.write(task.status)
            while task.status not in ('SUCCESS', 'ERROR'):
                fname = '{}/{}.log'.format('/tmp', task_id)
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
    return jsonify(task.info)


@celery.task(name='server.background_task', bind=True)
def background_task(self, function, args):
    logger = logging.getLogger(self.request.id)
    filehandler = logging.FileHandler("{}/{}.log".format('/tmp', self.request.id))
    logger.addHandler(filehandler)

    function = dill.loads(binascii.a2b_base64(function))
    args = dill.loads(binascii.a2b_base64(args))

    with contextlib.redirect_stdout(LoggerWriter(logger, 20)):
        return function(args)


class LoggerWriter:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message != '\n':
            self.logger.log(self.level, message)


if __name__ == '__main__':
    app.run(threaded=True)
