#!/usr/bin/env python3
"""Scrape the TD Ameritrade API Schemas.
"""
__author__ = 'Martin Blais <blais@furius.ca>'
__license__ = "GNU GPLv2"

from os import path
from typing import Any, Dict, List, Tuple, Union
import argparse
import json
import logging
import logging
import os
import pprint
import re
import tempfile
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome import options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Raw downloads scraped from the site. These get processed by another script
# into sanitized versions that can be processed.
DEFAULT_OUTPUT = path.join(path.dirname(path.dirname(__file__)), 'raw')


def CreateDriver(driver_exec: str = "/usr/local/bin/chromedriver",
                  headless: bool = False) -> WebDriver:
    """Create web driver instance with all the options."""
    opts = options.Options()
    opts.headless = headless
    return webdriver.Chrome(executable_path=driver_exec, options=opts)


def CleanName(name: str) -> str:
    """Clean up category and function names to CamelCase ids."""
    name = re.sub(r"\band\b", "And", name)
    name = re.sub(r"\bfor\b", "For", name)
    name = re.sub(r" a ", " A ", name)
    return re.sub(r" ", "", name)


def GetEndpoints(driver: WebDriver, trace: bool = False) -> Dict[str, str]:
    """Get a list of endpoints to fetch."""
    driver.get("https://developer.tdameritrade.com/apis")
    elem = driver.find_element_by_class_name('view-smartdocs-models')
    categories = {}
    for row in elem.find_elements_by_class_name('views-row'):
        category = CleanName(row.text.splitlines()[0])
        link = row.find_element_by_tag_name('a').get_attribute('href')
        categories[category] = link
    if trace:
        pprint.pprint(categories)

    # Process each of the categories.
    endpoints = []
    for catname, catlink in sorted(categories.items()):
        logging.info("Getting %s", catlink)
        driver.get(catlink)
        for row in driver.find_elements_by_class_name('views-row'):
            link = row.find_element_by_tag_name('a').get_attribute('href')
            method, funcname, apilink = row.text.splitlines()[:3]
            funcname = CleanName(funcname.strip())
            endpoints.append((catname, funcname, method, apilink, link))
    if trace:
        pprint.pprint(endpoints)

    return endpoints


def GetExampleAndSchema(driver: WebDriver) -> Tuple[str, str]:
    """Extract JSON schema and examples from an endpoint page."""
    # Attempt to get the data from the bottom table.
    # This is the schema for a POST request payload for upload.
    example = driver.execute_script('return jQuery("textarea.payload_text").val();')
    schema = driver.execute_script('return jQuery("textarea.payload_text_schema").val();')
    if example is None:
        # Attempt to get the date from the table on the right side.
        # This is the schema for the GET's response.
        example = driver.execute_script('return jQuery("textarea#response_body_example").val();')
        schema = driver.execute_script('return jQuery("textarea#response_body_schema").val();')
        if example is None:
            # Give up, there's probably no table.
            example = ''
            schema = ''
    return example, schema


def GetErrorCodes(driver: WebDriver) -> Dict[int, str]:
    """Extract a table of code -> message string."""
    elem = driver.find_element_by_class_name('table-error-codes')
    errcodes = {}
    for tr in elem.find_elements_by_class_name('listErrorCodes'):
        code, message = [td.text for td in tr.find_elements_by_tag_name('td')]
        errcodes[int(code)] = message
    return errcodes


def GetQueryParameters(driver: WebDriver) -> Dict[str, str]:
    """Extract the query parameters from the page."""
    query_params = {}
    try:
        div = driver.find_element_by_id('queryTable')
    except WebDriverException:
        return query_params
    table = div.find_element_by_tag_name('table')
    for row in table.find_elements_by_tag_name('tr'):
        row = [td.text for td in row.find_elements_by_tag_name('td')]
        if not row:
            continue
        name, description = row[0], row[2]

        match = re.match(r"(\S*)\s+\(required\)", name)
        if match:
            name = match.group(1)
            required = True
        else:
            required = False

        query_params[name] = {"description": description,
                              "required": required}
    return query_params


def WriteFile(filename: str, contents: Union[str, Any]):
    """Write a file, creating dir, conditionally, and with some debugging."""
    if not isinstance(contents, str):
        pprint.pprint(contents)
    logging.info("Writing: %s", filename)
    os.makedirs(path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as ofile:
        ofile.write(contents)


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__.strip())
    parser.add_argument('--output',
                        default=DEFAULT_OUTPUT,
                        help='Output directory to produce scraped API')
    args = parser.parse_args()

    # Create a Chrome WebDriver.
    driver = CreateDriver()
    logging.info("Getting %s", "https://developer.tdameritrade.com/apis")

    # Find the categories and their top-level links to each of the available API
    # endpoints.
    endpoints = GetEndpoints(driver)

    # Process each endpoint page, fetching related data with minimal process
    # (we'll post-process, to minimize traffic on the site from re-runs).
    if not path.exists(args.output):
        os.makedirs(args.output)
    for catname, funcname, method, apilink, link in endpoints:
        logging.info("Processing: %s %s", method, link)

        # Open the page.
        driver.get(link)

        # Fetch the schema and example.
        example, schema = GetExampleAndSchema(driver)

        # Get the table of error codes.
        errcodes = GetErrorCodes(driver)
        errcodes_json = json.dumps(errcodes, sort_keys=True, indent=4)

        # Get the query parameters.
        query_params = GetQueryParameters(driver)
        endpoint = {
            'method': method,
            'link': apilink,
            'query_params': query_params,
        }
        # TODO(blais): Also fetch and add the description and other information
        # from the page here. Furthermore, automatically insert the types of the
        # arugments from the URL as JSON schema as well.
        endpoint_json = json.dumps(endpoint, sort_keys=True, indent=4)

        # Write out the output files.
        dirname = path.join(args.output, funcname)

        # Write the schema. It is always either for a POST request payload or
        # for a GET response, there is never both of them.
        if schema:
            schema_filename = ("response.json"
                               if method == 'GET'
                               else "request.json")
            WriteFile(path.join(dirname, schema_filename), schema)

        WriteFile(path.join(dirname, "endpoint.json"), endpoint_json)
        WriteFile(path.join(dirname, "errcodes.json"), errcodes_json)
        WriteFile(path.join(dirname, "example.json"), example)

    logging.info("Done")


if __name__ == '__main__':
    main()
