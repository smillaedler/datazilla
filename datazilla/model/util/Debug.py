#####
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#####


from string import Template
import sys

#for debugging (do I even want an object in Python? - at least these methods
# are easily searchable, keep it for now)
import traceback

class D(object):

    @staticmethod
    def println(template, params=None):
        if (params is None):
            sys.stdout.write(template+"\n")
        else:
            sys.stdout.write(Template(template).safe_substitute(params)+"\n")

    @staticmethod
    def warning(template, params=None, cause=None):

        if isinstance(params, BaseException):
            cause=params
            params=None

        e = Except(template, params, cause, traceback.format_exc())
        D.println(str(e))

    #raise an exception with a trace for the cause too
    @staticmethod
    def error(template, params=None, cause=None):
        trace=traceback.format_exc()

        if isinstance(params, BaseException):
            cause=params
            params=None

        raise Except(template, params, cause, trace)  #placeholder 'till I know how that is done





D.info=D.println


class Except(Exception):
    def __init__(self, template=None, params=None, cause=None, trace=None):
        super(Exception, self).__init__(self)
        self.template=template
        self.params=params
        self.cause=cause
        self.causeTrace=trace

    @property
    def description(self):
        return Template(self.template).safe_substitute(self.params)

    def __str__(self):
        output=self.description

        if self.cause is not None:
            output+="\ncaused by\n"+self.cause.__str__()
        if self.causeTrace is not None:
            output+=self.causeTrace

        return output+"\n"