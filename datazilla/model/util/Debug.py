from string import Template
import sys

#for debugging (do I even want an object in Python? - at least these methods
# are easily searchable, keep it for now)
class D(object):

    @staticmethod
    def println(template, params):
        sys.stdout.write(Template(template).safe_substitute(params)+"\n")

    @staticmethod
    def warning(template, params, cause):
        if type(params) is Exception:
            cause=params
            params=None
        e = Except(template, params, cause)
        sys.stdout.write(e.toString())

    #raise an exception with a trace for the cause too
    @staticmethod
    def error(template, params, cause):
        if type(params) is Exception:
            cause=params
            params=None

        raise Except(template, params, cause)  #placeholder 'till I know how that is done





D.info=D.println


class Except(Exception):
    def __init__(self, template, params, cause):
        super(Exception, self).__init__(self)
        self.template=template
        self.params=params
        self.cause=cause

    @property
    def description(self):
        return Template(self.template).safe_substitute(self.params)

    def __str__(self):
        if self.cause is not None:
            return self.description+"\ncaused by\n"+self.cause.__str__()
        else:
            return self.description+"\n"