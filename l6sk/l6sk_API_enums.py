import enum

# To remain RESTful we indicate success on an individual API request by setting HTTP 200
# but in case of failure we might want to send back a description of the cause.
# and that means that response to at least some failures will be HTTP 200


class L6STATUS(enum.Enum):
    """ Status of an individual API request. """
    pass


