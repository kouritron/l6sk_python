#!/usr/bin/env python3
#
# Start a l6sk server

# -----
# pylint: disable=abstract-method
# this is needed because the way tornado works is that there are methods, we wont use unless we do want
# to use them, ie streaming data, ...

import os
import asyncio
import uuid
import json

from pathlib import Path

import tornado.escape
import tornado.ioloop
import tornado.locks
import tornado.web

import tornado.options as topts
# topts.define >>> to define new options
# topts.parse_command_line  >>> to parse argv
# topts.parse_config_file   >>> to parse a "server.conf" file
# topts.options             >>> Get the options from here

from l6sk import log_util as log

# ======================================================================================================================
# ======================================================================================================================
# ========================================================================================================= server setup
topts.define("port", default=1655, help="l6sk server port", type=int)
topts.define("debug", default=False, help="run in debug mode")


# ======================================================================================================================
# ======================================================================================================================
# =============================================================================================================== Routes
class L6_Index(tornado.web.RequestHandler):
    """ Handler for the l6sk homepage (ie /)

    ### Args: None
    ### Returns: l6sk homepage as html
    """

    def get(self):
        self.render("index.html", testdata=[1, 2, 3, 4, 5])


class L6_API_NEW_LGR(tornado.web.RequestHandler):
    """ Post a new log record to l6sk."""

    def post(self):
        pass
        # message = {"id": str(uuid.uuid4()), "body": self.get_argument("body")}
        # render_string() returns a "bytes", which is not supported in json. We need to get to a "str" + escaping
        # because we might paste this back into a returned template, and we dont want to allow for html injection.
        # message["html"] = tornado.escape.to_unicode(self.render_string("mytemplate.html", tpl_args=tpl_args))


class L6_API_HEALTH_CHECK(tornado.web.RequestHandler):
    def get(self):
        # you implement a superclass for all APIHandlers that has a
        # self.set_default_headers() method and set json response in there. and then ensure that all /api/...
        # handlers are subclass of APIHandlers ... You can also use .prepare() method from such a superclass.

        # or just set the headers once here.
        self.set_header("Content-Type", 'application/json')

        # TODO get this out of incoming get and echo it back to the user. we need to write JSON not html
        ping_id = self.get_argument("ping_id", default='ping0000')
        res = {
            'ping_id': ping_id,
            "err": "SUCC"
        }
        self.write(json.dumps(res))


# ======================================================================================================================
# ======================================================================================================================
# ================================================================================================================= main
def main():

    # ------------- setup tornado server
    topts.parse_command_line()

    repo_root = (Path(__file__) / '..' / '..').resolve()
    static_path = str(repo_root / 'l6sk_webui' / 'static')
    template_path = str(repo_root / 'l6sk_webui' / 'templates')
    server_port = topts.options.port

    # ------------- routing rules:
    # you can put regex in these URLs and get these tokens as args to handler.get(), handler.post(), handler.put()
    # the best place to put API docs is probably here in comments + the class docstring that is readable from here.
    # docs as python code would be a bit longer than docstring anyway. but docstring is still close enof to the
    # real thing that it should not fall out of sync.
    tor_app_routes = [
        (r"/", L6_Index),
        (r"/api/lgr/new", L6_API_NEW_LGR),
        (r"/api/healthchk", L6_API_HEALTH_CHECK),
    ]

    # --------- settings:
    tor_app_settings = {

        # This will serve static files from the given filesystem path for the URLs:
        # "/static/*", "/favicon.ico", "/robots.txt"
        # if you want to change these loot at: "static_url_prefix" setting
        'static_path': static_path,
        'template_path': template_path,
        'xsrf_cookies': True,
        'debug': topts.options.debug,
    }

    log.info(f"Starting log socket server on: {server_port}")
    log.info(f"Options: \n{json.dumps(tor_app_settings, sort_keys=True, indent=4)}")

    app = tornado.web.Application(tor_app_routes, **tor_app_settings)
    app.listen(server_port)
    tornado.ioloop.IOLoop.current().start()


if '__main__' == __name__:
    main()
