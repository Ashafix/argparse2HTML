import argparse
import itertools
import time
import builtins

parser1 = argparse.ArgumentParser(prog='simple math', description='a simple math command line interface')
parser1.add_argument('x', help='first value',
                     default='2',
                     type=int)
parser1.add_argument('y', help='second value',
                     default='3',
                     type=int)
parser1.add_argument('--action', help='which method to apply',
                     default='min', choices=['min', 'max', 'sum'],
                     type=str)

parser_cycler = argparse.ArgumentParser(prog='cycler')
parser_cycler.add_argument('--delay', help='delay in seconds',
                           default=0.1,
                           type=float)
parser_cycler.add_argument('--max', help='Number of iterations',
                           default=20,
                           type=int)
parser_cycler.add_argument('--characters', help='Cycle through those characters',
                           default='\\|/-',
                           type=str)

parser_wrapper = argparse.ArgumentParser(prog='wrapper')
parser_wrapper.add_argument('columns', help='List of comma separated column names',
                            default='a,b,c',
                            type=str)
parser_wrapper.add_argument('values', help='List of comma separated values',
                            default='1,2,3',
                            type=str)


def simple_math(args):
    vals = [args.x, args.y]
    f = getattr(builtins, args.action)
    return f(vals)


def cycler(args):
    for i, c in enumerate(itertools.cycle(args.characters)):
        print(c)
        time.sleep(args.delay)
        if i >= args.max:
            break
    return 'Finished after {} iterations'.format(i)


def wrapper(args):
    columns = args.columns.split(',')
    values = args.values.split(',')
    return complex_function(columns, values)


def complex_function(columns, values):
    resp = []
    for c, col in enumerate(columns):
        resp.append('{}: {}'.format(col, values[c]))
    return '\n'.join(resp)

