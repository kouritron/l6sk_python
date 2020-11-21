# pylint: disable=abstract-method
# even tho that seems like a reasonable warning, we still need to surpress it here because the way tornado works
# is that there are some methods, which wont be used by most users. but nonetheless they are there and
# raise NotImplementedError so pylint will complain about these.
#
# there is no better/nicer solution to this. Its just unintended conseqeunce and clash of style rules and
# good coding opinions between tornado and reasonable pylint defaults.
# This happens everywhere. The golang ppl tried to discourage exceptions as a matter of "better culture" but
# then ended up not only using panic/recover in the default http module, but they use it exactly as if
# it was a pythonic exception (the thing that supposedly doesnt exist in golang)


import os
import json

import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web

from l6sk import log_util as log



# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================================
# ======================================================================================================== Server Routes
class Index(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html", testdata=[1, 2, 3, 4, 5])


# ----------------------------------------------------------------------------------------------------------------------
class API_NEW_LGR(tornado.web.RequestHandler):
    def post(self):
        pass
        # message = {"id": str(uuid.uuid4()), "body": self.get_argument("body")}
        # render_string() returns a "bytes", which is not supported in json. We need to get to a "str" + escaping
        # because we might paste this back into a returned template, and we dont want to allow for html injection.
        # message["html"] = tornado.escape.to_unicode(self.render_string("mytemplate.html", tpl_args=tpl_args))


# ----------------------------------------------------------------------------------------------------------------------
class API_HCHK(tornado.web.RequestHandler):


    def get(self):
        # you can implement a superclass for all APIHandlers that has a
        # self.set_default_headers() method where you could set headers for json response in there.
        # and then ensure that all /api/... handlers subclass APIHandler ...
        # You can also use .prepare() method in a superclass to do things common to all subclasses.

        # or just set the headers once here.
        self.set_header("Content-Type", 'application/json')

        # TODO get this out of incoming get and echo it back to the user. we need to write JSON not html
        ping_id = self.get_argument("ping_id", default='ping0000')
        res = {'ping_id': ping_id, "err": "SUCC"}
        self.write(json.dumps(res))
