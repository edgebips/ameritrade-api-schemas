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


Author: Martin Blais <blais@furius.ca>
