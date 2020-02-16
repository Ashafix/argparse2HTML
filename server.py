import os
from collections import OrderedDict
import importlib
import socket
from flask import Flask, request, url_for, redirect
import jinja2

import args
from argparse2dict import argparser_to_dict
from config import CELERY_BROKER_URL, RESULT_BACKEND, USE_CELERY, SERVER_PORT

app = Flask(__name__)

if USE_CELERY:
    from blueprints.celery_task import app_with_celery
    app.config['CELERY_BROKER_URL'] = CELERY_BROKER_URL
    app.config['result_backend'] = RESULT_BACKEND

    app.config['task_track_started'] = True
    app.config['worker_redirect_stdouts'] = False
    app.config['worker_hijack_root_logger'] = False
    app.register_blueprint(app_with_celery)

else:
    from blueprints.subprocess_task import app_with_subprocess
    app.register_blueprint(app_with_subprocess)


TEMPLATE_FOLDER = './templates'
TEMPLATE_FILE = "default_template.html"

SERVER_NAME = socket.gethostbyname(socket.gethostname())


template_loader = jinja2.FileSystemLoader(searchpath=TEMPLATE_FOLDER)
template_env = jinja2.Environment(loader=template_loader)


@app.route('/')
def show_command_line_options():
    cmd = request.args.get('command')

    found, cli = args.get_cli(cmd)
    if not found:
        return redirect(url_for('list_available_commands'))
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


if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0')
