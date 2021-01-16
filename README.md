# TD Ameritrade API Schemas

This repositgory contains automatically scraped and cleaned up Apigee schemas
from the TD Ameritrade API webpage from:

    https://developer.tdameritrade.com/apis

The schemas aren't available for a number of
years and they don't change very frequently (but they do, to some extent), but
it's possible with some scraping magic to pull them in.

The schemas from the pages aren't proper JSON, they are interspersed with
comments. The scripts here do minimal cleaning in order to produce valid,
parseable JSON schema files.

## How to Use

The files are directly provided under `schemas`. Clone this repo and directly
process to convert to your favorite language or protocol, or validate.

## How to Update

Three phases:

1. Scrape updated downloads from the website:

        ./scripts/scrape_ameritrade_api.py

   This requires Selenium for Python with Chrome Webdriver. The site looks like
   an auto-generated site from and Apigee API so hopefully this should keep
   working for a while. This produces the raw downloaded files to the `raw`
   directory.

2. Convert the raw downloads to the sanitized schemas:

        ./scripts/convert_ameritrade_schemas.py

   This script will read the scraped files, clean them up and coalesce them into
   a single JSON file describing the endpoint under `schemas`.

3. Process the files to convert to your favorite language bindings or data
   types.


## Credentials

Martin Blais <blais@furius.ca>
