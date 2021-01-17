#!/usr/bin/env python3
"""Generate protocol buffer messages from the Ameritrade JSON schemas.
"""
# TODO(blais): DO NOT RUN. THIS ISN'T COMPLETE YET.

from os import path
from typing import Callable, Any, Iterable, Iterator, Union, Dict, List, Tuple
import argparse
import json
import logging
import textwrap
import functools
import os
import pprint
import tempfile
import subprocess
import io
import re


# Sanitized and cleaned up schemas.
_ROOT = path.normpath(path.dirname(path.dirname(__file__)))
DEFAULT_INPUT = path.join(_ROOT, 'schemas')

# Equivalent protocol buffer schemas
DEFAULT_OUTPUT = path.join(_ROOT, 'protos')


def PrintHeader(pr):
    pr('// -*- mode: protobuf -*-')
    pr('// THIS FILE IS AUTO-GENERATED.')
    pr()
    pr('syntax = "proto2";')
    pr()
    pr('package beancount;')
    pr()


def ProcessResponse(clsname: str, response: Dict[str, Any]):
    """Process an augmented response dict."""

    # Print the header.
    oss = io.StringIO()
    pr = functools.partial(print, file=oss)
    PrintHeader(pr)
    pr("message {} {{".format(clsname))
    pr()

    if 'top' in response:
        for name, json_schema in response['top'].items():
            proto_schema = ConvertJSONSchema(name, json_schema, pr)
            pr(proto_schema)

    # Output error codes.
    pr("  enum Error {")
    for index, (code, message) in enumerate(response['errors'].items(), 1):
        for line in textwrap.wrap(message, 60):
            pr("    // {}".format(line))
        pr("    HTTP_{} = {:d};".format(code, index))
    pr("  }")
    pr("  optional Error error_code = 1;")
    pr("}")

    return oss.getvalue()


## TODO(blais): This work is incomplete.
def ConvertJSONSchema(clsname: str, json_schema: Any, pr: Callable[[str], Any]) -> str:
    """Convert a JSON schema to a proto schema."""

    # TODO(blais):
    if json_schema is None:
        return ''


    pr("message {} {{".format(clsname))
    jdict_templates = set()
    for fname, jdict in json_schema.items():
        jtype = jdict['type']

        try:
            jdictcopy = jdict.copy()
            if jtype == 'object':
                if 'properties' in jdictcopy:
                    jdictcopy['properties'] = ()
                if 'additionalProperties' in jdictcopy:
                    jdictcopy['additionalProperties'] = ()
            if 'enum' in jdictcopy:
                jdictcopy['enum'] = ()
            jdict_templates.add(tuple(jdictcopy.items()))
        except TypeError:
            pprint.pprint(jdictcopy)
            raise
        continue

        pcard = 'optional'
        pdefault = None
        if jtype == 'string':
            ptype = 'string'
            if 'format' in jdict:
                jformat = jdict['format']
                if jformat == 'date-time':
                    ptype = 'string'
                else:
                    raise  NotImplementedError("Unknown format: {}".format(jformat))

            if 'enum' in jdict:
                ptype = 'enum'
                # TODO(blais): parse values.

        elif jtype == 'number' or jtype == 'integer':
            ptype = jdict['format']

        elif jtype == 'boolean':
            ptype = 'boolean'
            pdefault = jdict['default']

        elif jtype == 'array':
            xml = jdict['xml']
            if 'items' in jdict:
                items = jdict['items']
            ptype = 'Object'
            pcard = 'repeated'

        elif jtype == 'object':
            ptype = fname.capitalize()
            # TODO(blais): Continue

        else:
            raise NotImplementedError("Unknown type: {}".format(jtype))

        sdefault = ' [default = {}]'.format(pdefault) if pdefault is not None else ''
        pr("  {} {} {} = 1{};".format(pcard, ptype, fname, sdefault))
    pr("}")


    for template in sorted(jdict_templates):
        print(template)



def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('--clean_schemas', action='store',
                        default=DEFAULT_INPUT,
                        help="Directory path to read the raw downloaded data from.")
    parser.add_argument('--output', action='store',
                        default=DEFAULT_OUTPUT,
                        help=("Directory path to write the corresponding protocol buffer "
                              "schemas."))
    args = parser.parse_args()

    codes = {}

    # Iterator over all the files downloaded by the scraping script.
    for filename in os.listdir(args.clean_schemas):
        if not re.match(r"[A-Z].*.json", filename):
            continue
        with open(path.join(args.clean_schemas, filename)) as infile:
            schema = json.load(infile)

        print(schema['url'])
        print(schema['url_params'])
        print(schema['query_params'])
        # for code, description in schema['errors'].items():
        #     codes.setdefault(code, set()).add(description)

    pprint.pprint(codes)

    # for endpoint, request, response in convert_ameritrade_schemas.ParseSchemas(schemas_root):
    #     print("-" * 32, endpoint)
    #     string = ProcessResponse(endpoint, response)
    #     print(string)
    #     #break


if __name__ == '__main__':
    main()
