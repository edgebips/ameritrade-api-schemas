#!/usr/bin/env python3
"""Generate protocol buffer messages from the Ameritrade JSON schemas.
"""
# TODO(blais): DO NOT RUN. THIS ISN'T COMPLETE YET.

from os import path
from typing import Callable, Any, Iterable, Iterator, Union, Dict, List, Tuple, Optional
import argparse
import json
import logging
import copy
import collections
import hashlib
import textwrap
import functools
import os
import pprint
import tempfile
import subprocess
import io
import re
from pprint import pprint


# Sanitized and cleaned up schemas.
_ROOT = path.normpath(path.dirname(path.dirname(__file__)))
DEFAULT_INPUT = path.join(_ROOT, 'schemas')

# Equivalent protocol buffer schemas
DEFAULT_OUTPUT = path.join(_ROOT, 'proto', 'ameritrade.proto')


class TypeCallback:
    """A handler for each possible type seen in the schemas.

    This must be able to handle the following genericized types seen across all
    of the schemas:

      array {'type': 'array', 'xml': {'name': 'ITEM_TYPENAME', 'wrapped': True}, 'items': 'ITEM_TYPE...'}
      array {'items': 'ITEM_TYPE...', 'type': 'array'}
      boolean {'default': False, 'type': 'boolean'}
      boolean {'type': 'boolean'}
      integer {'format': 'int64', 'type': 'integer'}
      integer {'format': 'int32', 'type': 'integer'}
      integer {'format': 'int32', 'minimum': 0, 'type': 'integer'}
      number {'format': 'double', 'type': 'number'}
      number {'format': 'double', 'minimum': 0, 'type': 'number'}
      object {'type': 'object', 'properties': {}}
      object {'discriminator': 'DISCRIMINATOR', 'properties': {}, 'type': 'object'}
      object {'additionalProperties': 'ADD_PROP_TYPE...', 'type': 'object'}
      string {'enum': ['ENUMS...'], 'type': 'string'}
      string {'type': 'string'}
      string {'format': 'date-time', 'type': 'string'}

    """
    def Boolean(self, dtype): pass
    def Integer(self, dtype): pass
    def Float(self, dtype): pass
    def String(self, dtype): pass
    def Enum(self, dtype): pass
    def Object(self, dtype): pass
    def Array(self, dtype): pass


# An accumulator for the validation used to store accumulations of various tidbits.
ValidAccum = collections.namedtuple("ValidAccumuator", [
    # A dict of unique hash of a genericized type.
    # This is used to figure out all the possible types we need to handle.
    'type_signatures',

    # A mapping of enum field name to a list of such named enum type
    # definitions. These are later validated to ensure they're all equivalent
    # and used to deduplicate the definitions.
    'enums',

    # A mapping of discriminator field name to a list of such named enum type
    # definitions. These are reconciled later with their corresponding one-ofs.
    'disc_enums',
])


def ValidateTypeMap(typemap, name: str, accum: ValidAccum):
    """Process an object-map containing type values."""
    for field_name, dtype in sorted(typemap.items()):
        ValidateType(dtype, name, field_name, accum)


def ValidateType(dtype, parent_name: str, name: str, accum: ValidAccum):
    """Process an object containing a type."""

    # Remove optional attributes.
    # Note: We may use 'required' in the future.
    ctype = copy.deepcopy(dtype)
    ctype.pop('description', None)
    ctype.pop('required', None)

    subtype_map = None
    if ctype['type'] == 'boolean':
        assert set(ctype.keys()).issubset({'type', 'default'}), ctype

    elif ctype['type'] == 'integer':
        assert set(ctype.keys()).issubset({'type', 'format', 'minimum'}), ctype

    elif ctype['type'] == 'number':
        assert set(ctype.keys()).issubset({'type', 'format', 'minimum'}), ctype

    elif ctype['type'] == 'string':
        if 'enum' in ctype:
            # This is an enum type.
            assert set(ctype.keys()) == {'type', 'enum'}
            assert ctype['type'] == 'string'
            key = (parent_name, name)
            accum.enums.setdefault(key, []).append(dtype['enum'])
            ctype['enum'][:] = ['ENUMS...']

    elif ctype['type'] == 'object':
        # This is another anomaly in the schema, that field is typed 'object'
        # with no properties.
        if name == "purchasedDate" or name == 'ADD_PROP_ITEM':
            logging.warning("MISSING PROPERTIES: {}".format(ctype))
            ctype['properties'] = {}

        assert (set(ctype.keys()).issuperset({'type', 'properties'}) or
                set(ctype.keys()).issuperset({'type', 'additionalProperties'})), (name, ctype)

        assert set(ctype.keys()).issubset({'type', 'properties', 'additionalProperties',
                                           'discriminator', 'shortFormat'}), ctype

        if 'discriminator' in ctype:
            # Store the enum to reconcile against the type later.
            disc_field_name = ctype['discriminator']
            disc_enum = ctype['properties'][disc_field_name]['enum']
            accum.disc_enums.setdefault(disc_field_name, []).append(disc_enum)
            ctype['discriminator'] = 'DISCRIMINATOR'

        if 'properties' in ctype:
            subtype_map = ctype['properties']
            ctype['properties'] = {}

        elif 'additionalProperties' in ctype:
            subtype_map = {'ADD_PROP_ITEM': ctype['additionalProperties']}
            ctype['additionalProperties'] = 'ADD_PROP_TYPE...'

    elif ctype['type'] == 'array':
        assert set(ctype.keys()).issubset({'type', 'xml', 'items'}), ctype

        if 'items' not in ctype:
            # That's an abnormality which occurs only for 'childORder' and
            # 'replacingOrder' subtypes. Resolve those manually here.
            # TODO(blais): Remedy this manually here.
            logging.warning("MISSING SUBTYPE: {}".format(ctype))
            dtype['items'] = {}
        else:
            subtype_map = {'ARRAY_ITEMS': ctype['items']}
        ctype['items'] = "ITEM_TYPE..."

        if 'xml' not in ctype:
            # That's another abnormality which occcurs only for watchlists.
            # TODO(blais): Remedy this manually here.
            logging.warning("MISSING XML: {}".format(ctype))
            dtype['xml'] = {'name': '__UNKNOWN'}
        else:
            ctype['xml']['name'] = "ITEM_TYPENAME"

    else:
        raise NotImplementedError(str(dtype))

    # Insert the type signature in the output mapping.
    hsh = hashlib.md5()
    hsh.update(json.dumps(ctype, sort_keys=True).encode('utf8'))
    accum.type_signatures[hsh.digest()] = ctype

    if subtype_map:
        ValidateTypeMap(subtype_map, name, accum)


def CheckAllEqual(value_list, field_name):
    """Check that all the values in the `value_list` are equal."""
    value_iter = enumerate(value_list)
    _, first_value = next(value_iter)
    for index, value in value_iter:
        if value != first_value:
            msg = "Differing values for `{}` fields: 0 and {} differ".format(
                field_name, index)
            raise ValueError(msg)


# We have to remap a few: GetOptionChain and GetQuote both return a top-level
# type named 'Option' but they have slightly different definitions. This is how
# we assign globally unique types names where collisions occur. See
# {083508b4c37b}.
MSG_NAME_MAP = {
    ("Option", "GetOptionChain"): "OptionChainQuote",
    ("Option", "GetQuote"): "OptionQuote",
    ("Option", "GetQuotes"): "OptionQuote",
    ("Equity", "GetQuote"): "EquityQuote",
    ("Equity", "GetQuotes"): "EquityQuote",
}


ValidatedTypes = collections.namedtuple("ValidatedTypes", [
    # A dict of unique named types.
    'types',

    # A dict of unique named one-ofs.
    'oneofs',

    # A dict of unique named enums.
    'enums',
])


def ValidateSchemas(dirname: str) -> ValidatedTypes:
    """Validate that all the schema.

    Run each of the types through a validation routine which detects
    irregularities and accumulates unique type signatures we will need to
    convert to protos later.
    """

    # An accumulator for the validation.
    accum = ValidAccum({}, {}, {})

    # Accumulate a mapping of all the types see with the same name.
    named_oneof = collections.defaultdict(list)
    named_types = collections.defaultdict(list)

    # Iterate over all the files downloaded by the scraping script.
    for filename in sorted(os.listdir(dirname)):
        if not re.match(r"[A-Z].*.json", filename):
            continue
        with open(path.join(dirname, filename)) as infile:
            schema = json.load(infile)
        endpoint_name = schema['name']

        # Validate the top-level url params and query params.
        print("-------------- {:90} {}".format(schema['url'], filename))
        ValidateTypeMap(schema['url_params'], "Url", accum)
        ValidateTypeMap(schema['query_params'], "Query", accum)

        # Extract the mappings of top and sub types.
        if 'response' in schema:
            top = schema['response'].get("top", {})
            sub = schema['response'].get("sub", {})
            assert 'request' not in schema
            direction = 'response'
        elif 'request' in schema:
            top = schema['request'].get("top", {})
            sub = schema['request'].get("sub", {})
            assert 'response' not in schema
            direction = 'request'

        if not top and not sub:
            continue

        # Process all the subtypes first, validating their types and
        # accumulating lists of named objects in the process. A subtypes mapping
        # has two levels: the type of the OneOf and the subtype.
        for oneof_name, oneof_types in sub.items():
            # Save the one-of type.
            named_oneof[oneof_name].append(oneof_types)

            # Validate all the subtype objects within.
            for sub_name, sub_type_map in oneof_types.items():
                sub_name = MSG_NAME_MAP.get((sub_name, endpoint_name), sub_name)
                named_types[sub_name].append((endpoint_name, "sub", sub_type_map))
                ValidateTypeMap(sub_type_map, sub_name, accum)

        # Process all the top types, validating their types and accumulating
        # lists of named objects in the process. The top-level mapping has a
        # single level, the names of the types at top. print("TOP_TYPES",
        # endpoint_name, top.keys())
        for top_name, top_type in top.items():
            # We have one or two null subtypes. Probably an oversight on the
            # developers.
            if top_type is None:
                continue
            top_name = MSG_NAME_MAP.get((top_name, endpoint_name), top_name)
            named_types[top_name].append((endpoint_name, "top", top_type))
            ValidateTypeMap(top_type, top_name, accum)

    # Print all the unique type signatures to handle.
    print("-" * 120)
    print("Type signatures")
    for sig in sorted(accum.type_signatures.values(), key=lambda x: x['type']):
        print(sig['type'],sig)


    # Check that all the types with the same name have precisely the same
    # definition. With the message renamings abov this passes, which means we
    # can substantially simplify the entire final schema by factoring out these
    # types (which was expected, I'd have been surprised if the source had
    # slightly differing versions of these types). {083508b4c37b}

    # First check that all the one-of's are consistently defined.
    for name, value_list in named_oneof.items():
        CheckAllEqual(value_list, "oneof.{}".format(name))
    unique_named_oneof = {key: value[0] for key, value in named_oneof.items()}

    # Then check that all the message types are consistently defined.
    for name, value_list in named_types.items():
        if 1:
            # Output to files in order to debug the duplicates and craft a
            # rename map.
            os.makedirs("/tmp/schemas", exist_ok=True)
            for index, (endpoint, subtop, value) in enumerate(value_list):
                with open("/tmp/schemas/{}.{}.json".format(name, index), "w") as outfile:
                    print("{:80}".format(endpoint), file=outfile)
                    print("{:80}".format(subtop), file=outfile)
                    json.dump(value, outfile, sort_keys=True, indent=4)

        CheckAllEqual([v[2] for v in value_list], "type.{}".format(name))
    unique_named_types = {key: typelist[0][2] for key, typelist in named_types.items()}

    # Finally, check that all the discriminator enums are consistently defined.
    for enum_name, value_list in accum.disc_enums.items():
        CheckAllEqual(value_list, "disc_enum.{}".format(enum_name))

    # The other enums aren't, e.g., there
    unique_named_enums = {}
    for (_, enum_name), value_list in accum.enums.items():
        # Enums aren't unique; make them unique by their set of values and
        # assign them unique names.
        unique_sets = {}
        for value in value_list:
            hsh = hashlib.md5()
            for v in sorted(value):
                hsh.update(v.encode('utf8'))
            unique_sets[hsh.digest()] = value

        for index, evalues in enumerate(sorted(unique_sets.values()), start=1):
            key = enum_name if len(unique_sets) == 1 else "{}{}".format(enum_name, index)
            unique_named_enums[key] = evalues
        #CheckAllEqual(unique_value_list, "enum.{}".format(enum_name))

    # Now that we've validated consistency, deduplicate to obtain a final list
    # of all the types to generate.

    # Reconcile the oneofs with their enums, matching them one-to-one.
    # A discriminator maps to a one of a few OneOf maps.
    discriminator_maps = {
        'activityType': 'OrderActivity',
        'assetType': 'Instrument',
        'type': 'securitiesAccount',
    }

    # TODO(blais): Map and set these in the conversion.
    print("-" * 120)
    for name, oneof in named_oneof.items():
        print(name, oneof[0].keys())

    return ValidatedTypes(unique_named_types,
                          unique_named_oneof,
                          unique_named_enums)



def PrintHeader(pr):
    pr('// -*- mode: protobuf -*-')
    pr('// THIS FILE IS AUTO-GENERATED.')

    if True:
        pr('')
        pr("// WARNING: THIS ISN'T WORKING YET. DO NOT USE.")
        pr('')
    pr()
    pr('syntax = "proto2";')
    pr()
    pr('package ameritrade;')
    pr()


def Capitalize(string):
    return string[0].capitalize() + string[1:]


def GetProtoType(fname, ftype) -> Optional[str]:
    if not ftype:
        return None
    if ftype['type'] == 'boolean':
        return 'bool'
    elif ftype['type'] == 'integer':
        return ftype['format']
    elif ftype['type'] == 'number':
        return ftype['format']
    elif ftype['type'] == 'string':
        if 'enum' in ftype:
            return Capitalize(fname)  # TODO(blais):
        else:
            return 'string'
    elif ftype['type'] == 'object':
        if 'discriminator' in ftype:
            return 'oneof'  # TODO(blais):
        elif 'properties' in ftype:
            fname = re.sub('([a-zA-Z])', lambda x: x.groups()[0].upper(), fname, 1)
            return Capitalize(fname)  # TODO(blais):
        elif 'additionalProperties' in ftype:
            return Capitalize(fname)  # TODO(blais):
    elif ftype['type'] == 'array':
        return GetProtoType(ftype['xml']['name'], ftype['items'])
    else:
        raise NotImplementedError(str(ftype))


def GenerateEnum(pr, ename, evalues):
    pr("enum {} {{".format(Capitalize(ename)))
    for tag, value in enumerate(evalues, 1):
        pr("  {} = {};".format(value, tag))
    pr("}")


def GenerateType(pr, dname, dtype):
    pr("message {} {{".format(dname))
    for tag, (fname, ftype) in enumerate(dtype.items(), start=1):
        pcard = 'repeated' if 'array' in ftype else 'optional'
        ptype = GetProtoType(fname, ftype)
        pr("  {} {} {} = {};".format(pcard, ptype, fname, tag))

        # if 'top' in response:
        #     for name, json_schema in response['top'].items():
        #         proto_schema = ConvertJSONSchema(name, json_schema, pr)
        #         pr(proto_schema)

        # # Output error codes.
        # pr("  enum Error {")
        # for index, (code, message) in enumerate(response['errors'].items(), 1):
        #     for line in textwrap.wrap(message, 60):
        #         pr("    // {}".format(line))
        #     pr("    HTTP_{} = {:d};".format(code, index))
        # pr("  }")
        # pr("  optional Error error_code = 1;")

    pr("}")


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

    # Validate and deduplicate and clean the types.
    valid_types = ValidateSchemas(args.clean_schemas)

    # Convert to a proto schema.
    oss = io.StringIO()
    pr = functools.partial(print, file=oss)
    PrintHeader(pr)
    for ename, evalues in sorted(valid_types.enums.items()):
        GenerateEnum(pr, ename, evalues)
        pr()
    for dname, dtype in sorted(valid_types.types.items()):
        GenerateType(pr, dname, dtype)
        pr()
    with open(args.output, "w") as outfile:
        outfile.write(oss.getvalue())




if __name__ == '__main__':
    main()
