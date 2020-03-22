import argparse
from collections import OrderedDict


def argparser_to_dict(parser):
    """
    Converts an ArgumentParser from the argparse module to a dictionary
    :param parser: ArgumentParser, argparser which should be converted to a dictionary
    :return: dict, key: argparser.dest, value: dict with key: argparse.attribute and value: argparse.attribute_value
    """

    args = [a for a in parser._actions if type(a) not in (argparse._HelpAction, argparse._VersionAction)]
    arg_dict = OrderedDict()

    for arg in args:
        arg_dict[arg.dest] = {k: arg.__getattribute__(k) for k in dir(arg)
                              if (not k.startswith('_') and k not in ('container', ))}
        type_ = arg_dict[arg.dest].get('type')
        if type_ is not None:
            type_ = str(type_)
            if type_.startswith('<class') and "'" in type_:
                arg_dict[arg.dest]['type'] = type_.split("'")[1]
        default = arg_dict[arg.dest].get('default', False)
        if default is None:
            del arg_dict[arg.dest]['default']

    return arg_dict
