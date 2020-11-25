# -*- coding: utf-8 -*-
""" dbl dispatch: look at DBL_REQUEST_DISPATCH for what this module mostly does. """

import os
import sys
import random
import threading
import queue
from dataclasses import dataclass, field
import time

import typing
import enum

from l6sk import knobman as km
from l6sk.dbl.dbl_api import DBL_API
from l6sk import crypt_util

# careful w/ log or print() calls from this module. It has a dedicated thread and inf loop.
# a misplaced print() will turn this into a text generator program.
from l6sk import log_util as log

# ======================================================================================================================
# ======================================================================================================================

# ======================================================================================================================
# ======================================================================================================================


class DBL_REQ_PRIORITY(enum.Enum):

    # you could compare these values direcly: enum1.value >= enum2.value
    # the values also represent the probabilistic weight for servicing that queue in the event of a congestion.
    # so a value of 3 should have 3 times the chance of being serviced as a value of 1.
    # keep these values to small ints. dont do 100, 200, 300.
    LOW = 1
    NORMAL = 2
    HIGH = 3

    def __str__(self):
        return super().__str__()[17:]  # chopping classname out i.e. just leave LOW, NORMAL, ...


@dataclass
class DBL_REQ:

    op: DBL_API  # You can only request services offered by the DBL API as enumerated by "DBL_API"

    # optional, defaults to normal priority.
    priority: DBL_REQ_PRIORITY = field(default=DBL_REQ_PRIORITY.NORMAL)

    # operation specific data
    data: typing.Any = None

    # An old version of this had a status field {CREATED, SUCCESS, FAILED} and a result field (succ data or fail cause)
    # but this leads to a problem. There is risk of a race condition like so:
    # Imagine status is set to SUCCESS by DBL, some1 else (an HTTP request handler) might see this and try to read
    # result data which isnt set yet, and that request would be bongles. Just fatal to one request. but still its a
    # bug. And there is no such thing as small or large race condition.
    # one solution would be to put a lock on this object. I dont like this. Its too heavy handed.
    # an easier solution is like this. there are two fields:
    # - succ_data
    # - fail_cause
    # both inited to None. if either is not None, the request is finished. If fail_cause is set than it failed
    # if succ_data is set than request is fullfilled. Simple and no need for locking. Of course DBL should care
    # to not set both succ_data and fail_cause but if you do that, you have bigger problems than the race condition.
    succ_data: typing.Any = None
    fail_cause: typing.Any = None

    # each request gets a random uuid.
    # uuid: str = field(default_factory=lambda: crypt_util.get_uuid_generator().get_l6sk_uuid_b64())

    def __str__(self):
        # tmp_str = f"DBL_REQ(op={self.op}, priority={self.priority}, uuid={self.uuid}, data={self.data}, "
        # tmp_str += f"succ_data={self.succ_data}, fail_cause={self.fail_cause})"

        tmp_str = f"<{self.op}, {self.priority}, data:{self.data}, succ:{self.succ_data}, fail:{self.fail_cause}>"

        return tmp_str


class DBL_REQUEST_DISPATCH:
    """ This object manages the communication between HTTP request handlers and DB layer:
    HTTP request handlers (or any other DBL user) <<-------- req dispatch -------->> DB Layer

    **************************************** User side:
    The DBL user (could be sync or asnyc code) would just call the .put_req(req) method passing in an instance of
    DBL_REQ dataclass.

    This put_req() is not blocking, and returns pretty quickly. This is all the code that will run using
    the caller's thread and stack. After this the request is queued for processing by another thread that is the
    DBL worker thread. The DBL worker process this request eventually (possibly according to priority set in the req)
    and produce a success result or a cause of failure.
    This will be recorded in the request fields: <req.succ_data, req.fail_cause>
    Both of these start out None and this indicates a request that is not serviced yet. Once one of them is no longer
    the request has been served and the succ_data or fail_cause is populated accordingly.

    The way the caller would get back this result is very simple. Just sleep wait and check.
    You can use: asyncio.sleep(_time_) or time.sleep(_time_) depending on whether the caller is
    async (like a tornado app) or sync (like a cheroot app).

    ********** A few notes/myths about sleep waiting:
    At first glance this might sound like a primitve less than ideal solution but it isnt. Its actually pretty ideal.
    First it works for both async apps like tornado as well as multi threaded environments w/ forcing any choices on
    anyone.

    Supposedly we could've tried some sort of condition variable or future or promise or what not. But think about
    what this means: If we force the caller to do a cond.wait() it will block until DBL has called cond.notify()
    how does this work out with async code ?? not too well obviously. If there is a result queue things
    arent much different. What if we used future/promise/next cool thing to be added to in a future python.
    Now the sync code has to do await _the_cool_thing_ and its not gonna work.

    asyncio.sleep() can sleep for as little as a few milliseconds. we are doing a DB request after all. In case of a
    quick request/response API endpoint, this would at worst be a few milliseconds late compared to getting notified.
    in case of long polling API endpoint the DBL user is free to sleep for 1 second or more and still serve
    push notifications just fine. Obviously this is even easier for sync caller.

    A quick benchmark on my dev box(ubuntu18 + ryzen2700x) showed:
    asyncio.sleep(0.001) # 1 ms
    sleeps for approx. 1.1 ms milliseconds. mindblowing little overhead. but you are waiting for a DB operation
    and to reduce wasteful checking 10 ms or greater is recommended.

    ********** Note on priority. It is quite possible that the HTTP layer wants to assign different priorities to DBL
    requests. The idea is all requests get served if there is capacity, but if there is congestion than priortize
    some requests more than others.
    Example, a social media API. You get a "like" and a new "user content" both need recording. You might dispatch
    the "like" request as low priority, and get the DBL to prioritize DB capacity for recording the "user content"
    If the likes got delayed or worse yet build up too much until server crashed with ENOMEM or something
    its far less bad, than if the user content that was posted is lost.

    with this DBL implementation you get such features for free. Very few DBL designs even offer something like this.
    You cant offer such a feature, if someone is sleeping or awaiting for you to notify them.
    But if they "sleep wait", and they know they issued a low priority request they might even give up after a while
    and be ok. Or maybe dont sleep wait if you dont care for completion.

    ********** Also think about request lifecycle. DBL will drop this request object once its served, and
    it will be rdy for garbage collection once the caller dropped its reference. Its that simple. No need to
    put in an another result queue or dictionary, get caller to pick up, somehow ensure clean up and what not.
    There is no real risk of it getting leaked and excess build up in such data structures, even if request
    handler runs into a HTTP 500 or client gave up.

    **************************************** DBL side:
    ********** priority support:
    This is done by having multiple queues. i.e. lo_q, norm_q, hi_q, ....
    Recording a "like" may be a low_p operation. Some data that is needed to render UI may be high priority.

    If things arent congested everything gets to run. If DBL gets bombared with a bigger burst than "it + DB"
    can handle then it will priorotize higher queues for servicing. The its done is by making a random choice
    on which queue to service next. Say HIGH is 3 and LOW is 1. The hi_q will be 3 times as likely to be choosen as
    the lo_q for the next request service. This ensures no starvation while fairly priortizing higher p values.
    A PQueue could leade to starvation of even the NORMAL p values.
    We can also add a "starvation queue" called ultra_low_q or starv_q and set its p value to 0. This guy would only
    be serviced if others are empty, otherwise starve.
    """

    def __init__(self):
        super().__init__()

        # multiple queues for different priorities
        self._q_lo = queue.Queue()
        self._q_norm = queue.Queue()
        self._q_hi = queue.Queue()

    # dbg util method
    def _get_queue_name(self, q: queue.Queue) -> str:
        " Given one of this dipatcher's queues return a string telling humans which queue it was. (ie the lo, hi, ...)"

        if q == self._q_norm:
            return "<norm_q>"

        if q == self._q_lo:
            return "<lo_q>"

        if q == self._q_hi:
            return "<hi_q>"

        return "<unknown_q>"

    # ==================================================================================================================
    # ==================================================================================================================
    # ======================================================================================== HTTP request handler side
    # ==================================================================================================================
    # ==================================================================================================================
    def put_req(self, req: DBL_REQ):

        # log.info(f"put_req called. DBL_REQ: {req}")

        # default to normal priority. but it should be set properly already.
        dest_q = self._q_norm

        if req.priority == DBL_REQ_PRIORITY.HIGH:
            dest_q = self._q_hi

        if req.priority == DBL_REQ_PRIORITY.LOW:
            dest_q = self._q_lo

        # now deal with put no wait.
        try:
            dest_q.put_nowait(req)
        except Exception as ex:
            log.err(f"Failed to enqueue DBL request: {ex}")
            # TODO raise some sort of HTTP 500 or app specific exception. We are still on the request handler
            # thread so this goes to the correct entity. Other than the exception class all is well here.
            raise Exception("500 Internal Server Error")

        # Done request is in the correct queue. This is all the code that should run on the caller's thread.
        log.dbg(f"put_req succeded. DBL_REQ: {req}")

    # ==================================================================================================================
    # ==================================================================================================================
    # =========================================================================================== DBL worker thread side
    # ==================================================================================================================
    # ==================================================================================================================

    # **************************************** Get next request from dispatch queues.
    # def get_next_req(self) -> typing.Optional[DBL_REQ]:
    def get_next_req(self) -> typing.Union[DBL_REQ, None]:
        """ Find and return the next request from this dispatcher's request queues,
        according to scheduling fairness, if there are any requests. Return None otherwise.
        """

        # this is dangerous. it will turn the program into a forever loop log text generator.
        # log.dbg("get_next_req()")

        # ******************** weighted random queue choice
        # we have multiple queues with different priority values. we are gonna choose one to service.
        # we'll make a random choice but be more likely to choose the higher priority queues. While preferably avoid
        # starving the lower ones. That is unless the lowest one is a ultra low starve_q that should be starved
        # unless everyone else is empty.
        lo_q, norm_q, hi_q = self._q_lo, self._q_norm, self._q_hi

        lo_weight = DBL_REQ_PRIORITY.LOW.value
        norm_weight = DBL_REQ_PRIORITY.NORMAL.value
        hi_weight = DBL_REQ_PRIORITY.HIGH.value

        # TODO: normalize the weights but not so they sum to one. i.e. 10, 20, 30 become 1, 2, 3 not, 1/6, 2/6, 3/6
        # or we could just normalize. then zero out the weight if empty and use random."something else than choice"

        weighted_options = []

        # q.empty() method is not reliable. Actually it kinda is, its just that as soon as it returns its stale info.
        if not hi_q.empty():
            for _ in range(hi_weight):
                weighted_options.append(hi_q)

        if not norm_q.empty():
            for _ in range(norm_weight):
                weighted_options.append(norm_q)

        if not lo_q.empty():
            for _ in range(lo_weight):
                weighted_options.append(lo_q)

        # if weighted_options list is still empty, we could add starvation queue here, if there was a starv_q.

        # Now get the next DBL request.
        next_req = None

        # empty sequence is "falsy"
        if weighted_options:
            chosen_q = random.choice(weighted_options)  # chosen_q is now more likely to be hi_q than lo_q

            # log something about the q choice. This might be ok, because we would only generate a log msg if there
            # was a request.
            # named_weighted_options = [self._get_queue_name(wo) for wo in weighted_options]
            # log.dbg(f"q choice named_weighted_options: {named_weighted_options}")
            # log.dbg(f"q choice weighted_options: {weighted_options}")
            log.dbg(f"Weighted random choice q is: {self._get_queue_name(chosen_q)}")

            try:
                next_req = chosen_q.get_nowait()
            except queue.Empty:
                pass

        # Done. we found a request, with reasonable fairness, if there was any.
        return next_req


# ======================================================================================================================
# ======================================================================================================================
# ============================================================================================ DBL Service worker thread
# **************************************** Process a single DBL request.
def process_dbl_req(dao, next_req: DBL_REQ):

    # careful not to crash this thread. we need this thread in inf loop to keep serving requests,
    # even if 1 or 100 request fail miserably. ie db was out 5 minutes
    try:
        dao.serve_req(next_req)
    except:
        pass


# **************************************** entry point for DBL worker thread.
def dbl_service_thread_entry(dao_maker_callable, req_dispatch: DBL_REQUEST_DISPATCH):
    """ Entry point to the DBL worker service.
    This function needs a callable that will create a dao when invoked, and a req_dispatch object whose queues will
    be served forever by this thread.
    We dont take a dao (some DAOs like sqlite wont like getting created on one thread, and used from another).
    We take a callable that will create the DAO when called.

    Note: Maintaining the health of the underlying connection is the responsibility of the DAO
    and not the request dispatch layer. This layer's primary job is to decouple the DAO from the DBL user
    (ie request handlers) from dictating, or impacting each others threading models/decisions.

    Additionally consider that a long lived psql/mysql connection is not going to behave the same as a sqlite
    db file connection. You cant rely on a long lived network connection being there forever.
    For a file maybe you can. In any case its the DAO's responsibility. It could use a connection pool or some other
    mechanism. """

    sleep_timeout = km.get_knob("DBL_WORKER_THREAD_SLEEP_WAIT_TIMEOUT")
    idle_counter_threshold = km.get_knob("DBL_DISPATCH_IDLE_COUNTER_THRESHOLD")
    idle_counter = 0

    # assert idle_counter_threshold is positive int, otherwise refuse to init while still early.
    if (not isinstance(idle_counter_threshold, int)) or (idle_counter_threshold < 1):
        print("Init Error. Invalid DBL_DISPATCH_IDLE_COUNTER_THRESHOLD knob. Going to exiting now ...", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit()  # pylint: disable=protected-access

    dao = dao_maker_callable()

    # DBL thread never leaves this loop, careful exceptions must not break this loop, otherwise DBL is gone,
    # and the only planned/sensible recourse is to restart the web server process.
    while True:

        next_req = None
        try:
            # non-blocking. could return very fast, if queues are empty. blocking on a q dont make sense
            # since there are multiple queues. next_req could be None. It will be None if there truly nothing
            # but it might also be None if one was just inserted.
            next_req = req_dispatch.get_next_req()

        # Should be None if there is nothing. Exceptions are not expected here. if it happens, its a missed flaw.
        # An exception here could mean that msg exchange between web layer and DAO is impaired leaving no option
        # but server restart. Msg xchange is small amount of in-pprocess in-memory work.
        # It should be bullet proof and well tested.
        # Besides the testing we also need some sort of process manager/health check even inside a container.
        # Docker actually has a healthcheck feature, we could use that or build our own depending final packaging.
        # We still catch it to avoid losing the DBL worker thread inf loop. And ignore it if it happens,
        # beside logging a note. This might be a benefitial if only certain conditions cause this error.
        # on the other hand a crash could be good, to allow process manager to discover and restart it.
        except Exception as ex:
            log.err(f"Dispatch Error. Exception caught while looking for next request: {ex}")

        # Sleep wait if too idle mechanism. Careful not to lose the while loop.
        if next_req:
            # we got a request. Reset idle counter
            idle_counter = 0
            process_dbl_req(dao=dao, next_req=next_req)

        else:
            # we hit empty, inc idle counter, see if it exceeds threshold.
            idle_counter += 1

            if idle_counter > idle_counter_threshold:
                time.sleep(sleep_timeout)
                idle_counter -= 1  # dont let idle_counter to go to +inf.
        # Done, loop and process the next one.


# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
def main():
    r = DBL_REQ(op=DBL_API.HEALTH_CHK_1)
    print(r)


if '__main__' == __name__:
    main()
