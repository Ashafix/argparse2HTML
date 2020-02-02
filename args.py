from example_argparser import parser1, simple_math
from example_argparser import parser_cycler, cycler
from example_argparser import parser_wrapper, wrapper

from collections import namedtuple

Parser = namedtuple('CLI', ('name', 'parser', 'function'))


parsers = [Parser(name=parser1.prog,
                  parser=parser1,
                  function=simple_math),
           Parser(name=parser_cycler.prog,
                  parser=parser_cycler,
                  function=cycler),
           Parser(name=parser_wrapper.prog,
                  parser=parser_wrapper,
                  function=wrapper),
           ]
