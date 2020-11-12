
"""
DBL API. Expose the functionality provided by the l6sk DB Layer.

"""

import os
import threading
import queue
from dataclasses import dataclass

import typing
import enum
from abc import ABC, abstractmethod


# ======================================================================================================================
# ======================================================================================================================
# We use an enum to enumerate DBL API because the user is putting a request object on a queue.
# If they were calling a method something like abc.ABC abc.abstractmethod, .... would be better interface contract.
# The actual enum values (10, 20, 30, ....) can be ignored.
class DBL_API(enum.Enum):
    """ This is a enumeration of the operations exposed by the DB Layer to the web layer. Hence DBL_API. """

    # Create a user record. Could be used by the sign up system.
    CREATE_USER = 10

    # Update an existing user record. This could be used to, change password, change mutable user info ...
    # it could also be used to set a user to verified. multiple levels of it, if need be. email, phone, KYC, ...
    UPDATE_USER = 20

    # Get a user record. Could be used to grant login, display user info, ...
    DESCRIBE_USER = 30


    # ******************** Health checks
    # Health Check v1 is just for the DAO object to ACK health. Wont leave process. v2 reads db, v3 writes db
    # TODO acutally define v2 and v3.
    HEALTH_CHK_1 = 500
    HEALTH_CHK_2 = 501
    HEALTH_CHK_3 = 502

    def __str__(self):
        return super().__str__()[8:]  # chopping i.e. "DBL_API.CREATE_USER", to "CREATE_USER"

# This interface is a listing of the methods every dao must implement.
# Every DAO would subclass this and then have to implement all of its abstractmethods
# class DAOL6SK(ABC):

#     @abstractmethod
#     def health_check_v1(self):
#         """ . """

# ======================================================================================================================
# ======================================================================================================================
@dataclass(frozen=True)
class DBL_FAIL_CAUSE:

    # If the arisen situation corresponds to an http error, DAO can set it here. This will be None,
    # If DAO doesnt know or care.
    http_err_code = None

    # A short english msg that could be sent back to the user who made the HTTP request. Ok to show up in client logs.
    # Should not reveal internal data. The web layer might build an error page around this msg.
    user_msg: str = None

    # more detailed failure information. I strongly urge ppl to avoid saving the exception here. preferably "str(ex)"
    # storing the actual exception object has lots of implications. It has a ton of pointers to an entire
    # call stack none of which can be garbage collected as long as this pointer lives.
    dbg_data: typing.Any = None


# ======================================================================================================================
# ======================================================================================================================
def main():
    a = DBL_API.HEALTH_CHK_1
    print(f"{repr(a)}")


if '__main__' == __name__:
    main()
