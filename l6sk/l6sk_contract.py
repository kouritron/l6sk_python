"""
API contracts between various client and server implementations of l6sk (log socket)

This file is both used by the actual python l6sk implementation as well as tries to be as high level as possible
to also serve as a documentation file. The ultimate source of truth is truth from the codebase that doesnt ever
fall out of sync with the code.

"""

import enum
from os import sep
from l6sk import l6sk_api

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================================== API Doc
# NOTES:
# - you can put regex in these URLs and get a corresponding token sent to handler.get(), handler.post(), ... as args

L6SK_ROUTES = [
    (r"/", l6sk_api.Index),
    (r"/api/lgr/new", l6sk_api.API_NEW_LGR),
    (r"/api/hchk", l6sk_api.API_HCHK),
]

API_DOCS = """

======================================= ENDPOINT: /
- No args
- Returns: l6sk homepage as html

======================================= ENDPOINT: /api/lgr/new
- Post a new log record to this server.

*** REQUIRED Arg: lgr
    - The actual log record to be inserted as a JSON.

- OPTIONAL: sync_level
    - how long should this request wait before completion (ie client gets HTTP 200).
    - default: 0
    - 0: means this requests succeeds as soon as the server received a well formed the request.
    - 1: means wait till the record is fully processed by l6sk server and passed to the next layer (ie OS, DB, Disk)
    - 2: means wait till next layer confirms sync as well, ie fsync() or whatever else to assure durability.

----
#### JSON Response:
- requst status

======================================= ENDPOINT: /api/hchk

----
- Args:

- ping_id: DAS

----
Returns: health status as JSON

----
#### Example:
```
- GET /api/hchk
- Response:
{
    "health": ok
}
```
"""

# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================== Response JSON

# To remain RESTful we indicate success on an individual API request by setting HTTP 200
# but in case of failure we might want to send back a description of the cause.
# and that means that response to at least some failures will be HTTP 200


class L6STATUS(enum.Enum):
    """ Status of an individual API request. """


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================= print api docs
# for dev/dbg
def _print_api():

    sep_line_len = 100
    sep_line = '-' * sep_line_len

    print(sep_line)
    print(sep_line)
    print(sep_line)
    print(" l6sk routes:".rjust(sep_line_len, '-'))

    for endpoint in L6SK_ROUTES:
        url = str(endpoint[0]).ljust(40)
        handler = endpoint[1]
        print(f"{url}  --  {handler}")


    print('\n')
    print(sep_line)
    print(sep_line)
    print(sep_line)
    print(" l6sk API:".rjust(sep_line_len, '-'))
    print(API_DOCS)



# ======================================================================================================================
# ======================================================================================================================
if '__main__' == __name__:
    _print_api()
