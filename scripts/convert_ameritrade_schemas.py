#!/usr/bin/env python3
"""Convert and process the downloaded Ameritrade schemas to protocol buffers.

This script doesn't just read JSON files, it has to interpret the comments
inserted by the Ameritrade Java developers. I wish they thought about API
writers and provided a parseable description of their API, but they don't.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
from typing import Callable, Any, Iterable, Iterator, Union, Dict, List, Tuple
import argparse
import datetime
import hashlib
import json
import logging
import os
import pprint
import re
import subprocess
import tempfile

import parameters

# Raw downloads scraped from the site.
_ROOT = path.normpath(path.dirname(path.dirname(__file__)))
DEFAULT_INPUT = path.join(_ROOT, 'raw')

# Sanitized and versions output that can be processed.
DEFAULT_OUTPUT = path.join(_ROOT, 'schemas')


JSON = Union[str, int, float, Dict[str, 'JSON'], List['JSON']]


def Diff(string1: str, string2: str):
    with tempfile.NamedTemporaryFile('w') as tmpfile1:
        tmpfile1.write(string1)
        tmpfile1.flush()
        with tempfile.NamedTemporaryFile('w') as tmpfile2:
            tmpfile2.write(string2)
            tmpfile2.flush()
            subprocess.call(["diff", tmpfile1.name, tmpfile2.name])


def ReadJson(filename: str) -> JSON:
    with open(filename) as infile:
        return json.load(infile)


def SplitSequence(iterable: Iterable[Any],
                  start_pred: Callable[[Any], bool] = None,
                  filter_pred: Callable[[Any], bool] = None) -> List[List[Any]]:
    """Split a sequence across empty elements."""
    if start_pred is None:
        start_pred = bool
    blocks = []
    block = []
    for elem in iterable:
        if start_pred(elem):
            if block:
                blocks.append(block)
                block = []
        if filter_pred is None or filter_pred(elem):
            block.append(elem)
    if block:
        blocks.append(block)
    return blocks


def IterBy(iterable: Iterable[Any], by: int) -> Iterator[Tuple[Any, Any]]:
    """Iterate over consecutive pairs of elements."""
    itor = iter(iterable)
    while True:
        try:
            yield [next(itor) for _ in range(by)]
        except StopIteration:
            break


def SplitGroups(group_string: str) -> Dict[str, JSON]:
    """Split the top groups and yield pairs of (name, contents)."""
    top_groups = re.split(r"^\s*//(.*):", group_string,
                          flags=re.MULTILINE)
    assert not top_groups[0]
    del top_groups[0]
    assert len(top_groups) % 2 == 0
    return dict(IterBy(top_groups, 2))


def SplitSubTypes(remainder: str) -> Dict[str, Dict[str, JSON]]:
    """Split the remaining subtypes and yield a dict of type to list of types."""
    subtypes = re.split(r'^//The class <([A-Za-z]+)> has the following subclasses:'
                        '.*?listed below:\s*$',
                        remainder, flags=re.MULTILINE|re.DOTALL)
    assert not subtypes[0]
    del subtypes[0]
    assert len(subtypes) % 2 == 0

    subdict = {}
    for stname, stcontents in IterBy(subtypes, 2):
        # Split by OR to get and check the number of one-ofs in the subtype.
        alternatives = re.split(r"^//OR", stcontents, flags=re.MULTILINE)

        stcontents = re.sub(r"^//OR", "", stcontents, flags=re.MULTILINE)
        altdict = SplitGroups(stcontents)
        assert len(altdict) == len(alternatives)

        # Parse the values and associated to the subtype for output.
        altdict = {name: ParseJSON(value)
                   for name, value in altdict.items()}
        subdict[stname] = altdict

    return subdict


def ParseJSON(string: str) -> JSON:
    """A JSON parser a little more tolerant."""
    string = string.strip()
    if re.match(r"undefined", string):
        return None
    else:
        try:
            return json.loads(string)
        except json.JSONDecodeError:
            pprint.pprint(string)
            raise


def ReadJsonWithComments(filename: str) -> JSON:
    """Read and parse a JSON file with comment separators."""
    with open(filename) as schfile:
        #print("-" * 40,filename)

        # Check for error file.
        # TODO(blais): This should be fixed upstream.
        orig_contents = contents = schfile.read()
        if re.search(r"\bWebServiceError\b", contents):
            return {}

        # Normalize the top-level list of message definitions to be surrounded
        # by [...] and to include a declaration name.
        if re.match(r"\{", orig_contents.lstrip()):
            contents = "//{}:\n{}".format(
                path.basename(path.dirname(filename)), contents)
        if not re.match(r"\[", contents.lstrip()):
            contents = "[\n{}".format(contents)
            if re.search(r"//The class", contents):
                contents = re.sub(r"^\s*(//The class.*)$", r"]\n\1", contents,
                                  count=1, flags=re.MULTILINE)
            else:
                contents = "{}\n]\n".format(contents)

        # Parse the initial list of messages.
        topmatch = re.match(r"^\[(.*)^\]", contents, flags=re.MULTILINE|re.DOTALL)
        assert topmatch
        top_messages = SplitGroups(topmatch.group(1).strip())
        output = {'top': {name: ParseJSON(group)
                          for name, group in top_messages.items()}}

        # Parse subtypes.
        remainder = contents[topmatch.end():].lstrip()
        if remainder:
            subtypes = SplitSubTypes(remainder)
            output['sub'] = subtypes

        return output


def ParseSchemas(raw_dir: str) -> List[Tuple[str, Any, Any]]:
    """Parse the schemas. Return a list of (request, response) dicts."""
    # Walk two levels of schema dirs.
    rrpairs = []
    for root, dirs, files in os.walk(raw_dir):
        if dirs:
            continue
        endpoint_name = path.basename(root)

        # Read a JSON describing the high-level endpoint URL, method and query
        # parameters, and embed the possible error codes in it.
        endpoint = ReadJson(path.join(root, 'endpoint.json'))
        errcodes = ReadJson(path.join(root, 'errcodes.json'))
        endpoint['errors'] = errcodes

        # Infer and embed the data types for the URL parameters. Convert them to
        # their JSON schema equivalents.
        url_params = endpoint['url_params'] = {}
        for match in re.finditer('{(.*?)}', endpoint['url']):
            param_name = match.group(1)
            url_params[param_name] = parameters.URL_PARAM_TYPES[param_name]

        # Infer and embed the data types of the query parameters. Insert them
        # into the descriptions and required fields from the already fetched
        # query params description.
        for name, value in endpoint['query_params'].items():
            dtype = parameters.URL_PARAM_TYPES[param_name]
            value.update(dtype)

        # Parse the request, if present.
        filename = path.join(root, 'request.json')
        if path.exists(filename):
            endpoint['request'] = ReadJsonWithComments(path.join(root, 'request.json'))

        # Parse the response, if present.
        filename = path.join(root, 'response.json')
        response = None
        if path.exists(filename):
            endpoint['response'] = ReadJsonWithComments(path.join(root, 'response.json'))

        # Insert the name of the endpoint itself.
        endpoint['name'] = endpoint_name

        rrpairs.append((endpoint_name, endpoint))

    return rrpairs


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('--raw_downloaded_data', action='store',
                        default=DEFAULT_INPUT,
                        help="Directory path to read the raw downloaded data from.")
    parser.add_argument('--output', action='store',
                        default=DEFAULT_OUTPUT,
                        help="Directory path to write the clean, sanitized version to.")
    args = parser.parse_args()

    # Iterator over all the files downloaded by the scraping script, sanitize
    # and coalesce each of the raw files into a single JSON tuple out to a
    # single file describing the service endpoint.
    os.makedirs(args.output, exist_ok=True)
    hashes = {}
    for name, endpoint in ParseSchemas(args.raw_downloaded_data):
        logging.info("Processing %s", name)
        filename = path.join(args.output, "{}.json".format(name))
        with open(filename, 'w') as outfile:
            json.dump(endpoint, outfile, sort_keys=True, indent=4)

        hsh = hashlib.sha256()
        with open(filename, 'rb') as infile:
            hsh.update(infile.read())
        hashes[name] = hsh

    # Produce a unique hash of all the cleaned up input data. You can use this
    # as a version number. This is not an integer, but a hash of the input; if
    # the input is identical, the hash hasn't changed.
    hsh = hashlib.sha256()
    for name, msghash in sorted(hashes.items()):
        hsh.update(name.encode('ascii'))
        hsh.update(msghash.digest())
    version = {
        'hash': hsh.hexdigest(),
        'date': datetime.date.today().isoformat(),
        'messages': {name: msghash.hexdigest()
                     for name, msghash in sorted(hashes.items())}
    }
    with open(path.join(args.output, "version.json"), 'w') as versfile:
        json.dump(version, versfile, sort_keys=True, indent=4)


if __name__ == '__main__':
    main()
