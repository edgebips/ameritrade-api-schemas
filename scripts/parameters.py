"""Type definitions that aren't provided by the site.

This covers the arguments embedded in the URLs as well as the query parameters,
both of which do not have type definitions. Unfortunately, these were created
manually and are pulled in by the convert_ameritrade_schemas script.
"""

# Type definitions for all the known URL params, key'ed by parameter name.
URL_PARAM_TYPES = {
    'accountId': {
        "format": "int64",
        "type": "integer"
    },
    'cusip': {
        "type": "string"
    },
    'index': {
        "type": "string"
    },
    'market': {
        "type": "string"
    },
    'orderId': {
        "format": "int64",
        "type": "integer"
    },
    'savedOrderId': {
        "format": "int64",
        "type": "integer"
    },
    'symbol': {
        "type": "string"
    },
    'transactionId': {
        "format": "int64",
        "type": "integer"
    },
    'watchlistId': {
        "type": "string"
    },
}

# Type definitions for all the known query params across all the calls, key'ed
# by parameter name.
#
# A value of type dict indicates a single type. A value of type tuple indicates
# the parameter name maps to one of many types. In that case, the tuple contains
# pairs of (regexp, type) where the `regexp` is to be matched against the
# description to select which to use. This is an unfortunate consequence of the
# API developers not choosing unique semantics for each name.
QUERY_PARAM_TYPES = {
    "accountId": {
        "format": "int64",
        "type": "integer",
    },
    "accountIds": {
        "type": "array",
        "items": {
            "type": "integer",
            "format": "int64",
        }
    },
    "apikey": {
        "type": "string",
    },
    "change": {
        "enum": [
            "PERCENT",
            "VALUE",
        ],
        "type": "string",
    },
    "contractType": {
        "enum": [
            "CALL",
            "PUT",
            "ALL",
        ],
        "type": "string",
    },
    "date": {
        "format": "date-time",
        "type": "string",
    },
    "daysToExpiration": {
        "type": "integer",
        "format": "int64",
    },
    "direction": {
        "enum": [
            "UP",
            "DOWN",
        ],
        "type": "string",
    },
    "endDate": [
        ("milliseconds", {
            "type": "integer",
            "format": "int64",
        }),
        ("yyyy-MM-dd", {
            "type": "string"
        })
    ],
    "expMonth": {
        "enum": [
            "ALL",
            "JAN",
            "FEB",
            "MAR",
            "APR",
            "MAY",
            "JUN",
            "JUL",
            "AUG",
            "SEP",
            "OCT",
            "NOV",
            "DEC",
        ],
        "type": "string",
    },
    "fields": [
        ("streamerSubscriptionKeys", {
            "type": "array",
            "items": {
                "enum": [
                    "streamerSubscriptionKeys",
                    "streamerConnectionInfo",
                    "preferences",
                    "surrogateIds",
                ],
                "type": "string"
            }}),
        ("Balances displayed by default", {
            "type": "array",
            "items": {
                "enum": [
                    "positions",
                    "orders",
                ],
                "type": "string"
            }})
    ],
    "frequency": {
        "enum": [
            "minute",
            "daily",
            "weekly",
            "monthly",
        ],
        "type": "string",
    },
    "frequencyType": {
        "enum": [
            "minute",
            "daily",
            "weekly",
            "monthly",
        ],
        "type": "string",
    },
    "fromDate": [
        ("yyyy-MM-dd\"T\"HH:mm:ssz", {
            "format": "date-time",
            "type": "string",
        }),
        ("Date must be within 60 days", {
            "type": "string"
        })
    ],
    "includeQuotes": {
        "type": "boolean"
    },
    "interestRate": {
        "format": "double",
        "type": "number"
    },
    "interval": {
        "format": "double",
        "type": "number"
    },
    "markets": {
        "enum": [
            "EQUITY",
            "OPTION",
            "FUTURE",
            "BOND",
            "FOREX",
        ],
        "type": "string",
    },
    "maxResults": {
        "format": "int32",
        "type": "integer"
    },
    "needExtendedHoursData": {
        "type": "boolean"
    },
    "optionType": {
        "enum": [
            "S",
            "NS",
            "ALL",
        ],
        "type": "string",
    },
    "period": {
        "format": "int32",
        "type": "integer"
    },
    "periodType": {
        "enum": [
            "day",
            "month",
            "year",
            "ytd",
        ],
        "type": "string",
    },
    "projection": {
        "enum": [
            "symbol-search",
            "symbol-regexp",
            "desc-search",
            "desc-regex",
            "fundamental",
        ],
        "type": "string",
    },
    "range": {
        "enum": [
            "ITM",
            "NTM",
            "OTM",
            "SAK",
            "SBK",
            "SNK",
            "ALL",
        ],
        "type": "string",
    },
    "startDate": [
        ("milliseconds", {
            "type": "integer",
            "format": "int64",
        }),
        ("yyyy-MM-dd", {
            "type": "string"
        }),
    ],
    "status": {
        "enum": [
            "AWAITING_PARENT_ORDER",
            "AWAITING_CONDITION",
            "AWAITING_MANUAL_REVIEW",
            "ACCEPTED",
            "AWAITING_UR_OUT",
            "PENDING_ACTIVATION",
            "QUEUED",
            "WORKING",
            "REJECTED",
            "PENDING_CANCEL",
            "CANCELED",
            "PENDING_REPLACE",
            "REPLACED",
            "FILLED",
            "EXPIRED"
        ],
        "type": "string"
    },
    "strategy": {
        "enum": [
            "SINGLE",
            "ANALYTICAL",
            "COVERED",
            "VERTICAL",
            "CALENDAR",
            "STRANGLE",
            "STRADDLE",
            "BUTTERFLY",
            "CONDOR",
            "DIAGONAL",
            "COLLAR",
            "ROLL"
        ],
        "type": "string"
    },
    "strike": {
        "format": "double",
        "type": "number"
    },
    "strikeCount": {
        "format": "int32",
        "type": "integer"
    },
    "symbol": {
        "type": "string"
    },
    "toDate": {
        "format": "date-time",
        "type": "string",
    },
    "toEnteredTime": {
        "type": "string",
    },
    "type": {
        "enum": [
            "ALL",
            "TRADE",
            "BUY_ONLY",
            "SELL_ONLY",
            "CASH_IN_OR_CASH_OUT",
            "CHECKING",
            "DIVIDEND",
            "INTEREST",
            "OTHER",
            "ADVISOR_FEES",
        ],
        "type": "string"
    },
    "underlyingPrice": {
        "format": "double",
        "type": "number"
    },
    "volatility": {
        "format": "double",
        "type": "number"
    },
}
