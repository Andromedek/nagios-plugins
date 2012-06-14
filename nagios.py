'''
Created on May 29, 2012

@author: yangming
@copyright: appfirst inc.
'''
import argparse, sys
import os, pickle

class Status(object):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3

    @staticmethod
    def to_status(status_code):
        if status_code == Status.OK:
            return 'OK'
        elif status_code == Status.WARNING:
            return 'WARNING'
        elif status_code == Status.CRITICAL:
            return 'CRITICAL'
        else:
            return 'UNKNOWN'

class Result(object):
    def __init__(self, service, status_code, message):
        self.service = service.upper()
        self.status_code = status_code
        self.status = Status.to_status(status_code)
        self.message = message
        self.perf_data_list = []
        self.exit_code = self.get_exit_code(status_code)

    def get_exit_code(self, status_code):
        return status_code

    def add_performance_data(self, label, value, UOM=None,
                             warn=None, crit=None, minv=None, maxv=None):
        perfdata = {'label':label,'value':value,'UOM' :UOM,
                    'warn' :warn, 'crit' :crit, 'minv' :minv, 'maxv' :maxv}
        self.perf_data_list.append(perfdata)
        return self

    def __str__(self):
        output = '{0} {1}: {2}'.format(self.service, self.status, self.message)
        if len(self.perf_data_list):
            output += ' |'
        for pd in self.perf_data_list:
            output += self._get_perfdata_output(pd)
        return output

    def _get_perfdata_output(self, perfdata):
        pdline = " {0}={1}".format(perfdata["label"], perfdata["value"])
        if perfdata["UOM"] is not None:
            pdline += perfdata["UOM"]
        if perfdata["warn"] is not None:
            pdline += ';%s' % perfdata["warn"]
        if perfdata["crit"] is not None:
            pdline += ';%s' % perfdata["crit"]
        if perfdata["minv"] is not None:
            pdline += ';%s' % perfdata["minv"]
        if perfdata["maxv"] is not None:
            pdline += ';%s' % perfdata["maxv"]
        return pdline

class BasePlugin(object):
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self._default_argument()

    def _default_argument(self):
        self.parser.add_argument("-w", "--warn", type=int, required=False)
        self.parser.add_argument("-c", "--crit", type=int, required=False)

    def _parse_range(self, range_str):
        pass

    def run(self):
        self.request = self.parser.parse_args(sys.argv[1:])
        result = self.check(self.request)
        if result is not None:
            print result
            sys.exit(result.exit_code)

    def check(self, request):
        raise NotImplementedError('need to override BasePlugin.check in subclass')

    def verdict(self, value, request):
        # default verdict function
        # ok   if value <  warn             crit
        # warn if          warn <= value <  crit
        # crit if          warn             crit <= value
        status_code = Status.UNKNOWN
        if request.warn is not None and value < request.warn:
            status_code = Status.OK
        elif request.crit is not None and value >= request.crit:
            status_code = Status.CRITICAL
        elif request.warn is not None:
            status_code = Status.WARNING
        else:
            status_code = Status.OK
        return status_code

class BatchStatusPlugin(BasePlugin):
    def __init__(self):
        super(BatchStatusPlugin, self).__init__()
        self.parser.add_argument("-d", "--rootdir", required=False,
                                 default='/tmp/', type=str);
        self.parser.add_argument("-t", "--type", required=True,
                                 choices=self.__class__.commandmap.keys());

    def check(self, request):
        if hasattr(self.__class__, "commandmap"):
            commandmap = self.__class__.commandmap
            if request.type in commandmap and commandmap[request.type]:
                result = commandmap[request.type](self, request)
                if result:
                    return result
        return Result(request.type, Status.UNKNOWN, "mysterious status")

    @classmethod
    def command(cls, command_str, manner=None):
        if not hasattr(cls, "commandmap"):
            cls.commandmap = {}
        def add_command(method):
            if manner == "cumulative":
                method = BatchStatusPlugin.cumulative(method)
            elif manner == "status":
                method = BatchStatusPlugin.status(method)
            cls.commandmap[command_str] = method
            return method
        return add_command

    @staticmethod
    def cumulative(method):
        def new_command(self, request):
            self.stats = self.parse_status_output(request)
            if len(self.stats) == 0:
                return Result(request.type, Status.CRITICAL,
                                     "cannot get service status.")
            self.laststats = self.retreive_last_status(request)
            result = method(self, request)
            self.save_status(request)
            return result
        return new_command

    @staticmethod
    def status(method):
        def new_command(self, request):
            self.stats = self.parse_status_output(request)
            if len(self.stats) == 0:
                return Result(request.type, Status.CRITICAL,
                                     "cannot get service status.")
            return method(self, request)
        return new_command

    def parse_status_output(self, request):
        raise NotImplementedError('need to override BasePlugin.check in subclass')

    def retreive_last_status(self, request):
        laststats = {}
        try:
            fn = os.path.join(request.rootdir, request.filename)
            if os.path.exists(fn):
                laststats = pickle.load(open(fn))
        except pickle.PickleError:
            pass
        except EOFError:
            pass
        return laststats

    def save_status(self, request):
        try:
            fn = os.path.join(request.rootdir, request.filename)
            pickle.dump(self.laststats, open(fn, "w"))
        except pickle.PickleError:
            pass
        except EOFError:
            pass

    def get_delta_value(self, attr):
        if attr in self.laststats:
            delta = self.stats[attr] - self.laststats[attr]
        else:
            delta = self.stats[attr]
        self.laststats[attr] = self.stats[attr]
        return delta