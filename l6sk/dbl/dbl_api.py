
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
    """ Fields:

    ---
    ### http_err_code:
    If the arisen situation corresponds to an http error, DAO will set it here.
    If DAO doesnt know or doesnt care, This will be None.

    ---
    ### user_msg:
    A short english msg that could be sent back to the user who made the HTTP request if necessary. Again DAO will
    only produce such a message if it can. otherwise None. The message must be such that its OK to show up
    on the client side or client logs, .... It should not reveal internal data. Its upto the web to use it or not.

    ---
    ### dbg_info_string:
    More detailed failure information. This should not be sent out to any clients.
    It is strongly advised to not save an exception here. Saving "str(ex)" is ok, because its just a string.
    but storing the actual exception object has lots of implications. It has a ton of pointers to an entire
    call stack none of which can be garbage collected as long as this pointer lives.
    """

    http_err_code = None
    user_msg: str = None
    dbg_info_string: str = None


# ======================================================================================================================
# ======================================================================================================================
def main():
    a = DBL_API.HEALTH_CHK_1
    print(f"{repr(a)}")


if '__main__' == __name__:
    main()
