#!/usr/bin/python -O
#
# Author: Vladislav Nazarenko <vnazarenko@codeberry.de>
# Source: https://github.com/talset/apache-tools
#
#
# File: httpd.conf
#
#        JkWorkersFile /etc/httpd/conf.d/workers.properties
#        JkLogFile "| /usr/sbin/rotatelogs -l /var/log/httpd/mod_jk-%Y-%m-%d.%H.log 3600"
#        JkLogLevel error
#        JkLogStampFormat "[%a %b %d %H:%M:%S %Y]"
#        JkOptions +ForwardKeySize -ForwardDirectories +ForwardURICompatUnparsed
#        JkShmFile [PATH]../jk.shm
#        JkMount /jkstatus/* status
#        JkMount /* [BALANCER NAME]
#
# File: workers.properties
#
#        worker.status.type=status
#
#        worker.template.type=ajp13
#        worker.template.socket_timeout=180
#        worker.template.socket_connect_timeout=5000
#        worker.template.retries=2
#        worker.template.recovery_options=3
#        worker.template.distance=0
#
#        worker.appsrv00.reference=worker.template
#        worker.appsrv00.host=app01.example.com
#        worker.appsrv00.port=8080
#        worker.appsrv01.reference=worker.template
#        worker.appsrv01.host=app01.example.com
#        worker.appsrv01.port=9080
#        worker.appsrv10.reference=worker.template
#        worker.appsrv10.host=app02.example.com
#        worker.appsrv10.port=8080
#        worker.appsrv11.reference=worker.template
#        worker.appsrv11.host=app02.example.com
#        worker.appsrv11.port=9080
#
#        worker.appsrv.type=lb
#        worker.appsrv.method=B
#        worker.appsrv.recover_time=30
#        worker.appsrv.balance_workers=appsrv00 appsrv01 appsrv00 appsrv01
#
#        worker.list=status appsrv
#
#
# You have to allow /jkstatus
#
#        <Location /jkstatus>
#                Order deny,allow
#                Deny from all
#                Allow from localhost 127.0.0.1
#        </Location>
#
# Verify url="http....."
#
#
# HOW TO :
#        balancer-manager.py -l
#        balancer-manager.py -w ajp://10.152.45.1:8001 -a enable
#
#############################################################################

import argparse
import re
import HTMLParser
import sys
import urlparse

from urllib  import urlencode
from urllib2 import Request
from urllib2 import urlopen

#############################################################################
# Get args
PARSER = argparse.ArgumentParser()
PARSER.add_argument("-H", "--host", help="Host connect to", type=str)
PARSER.add_argument("-p", "--port", help="Port connect to", type=str)
PARSER.add_argument("-l", "--list",
            help="List Worker member and status", action='store_true')
PARSER.add_argument("-a", "--action",
            help="\"enable\" or \"disable\" the specified Worker", type=str)
PARSER.add_argument("-w", "--worker",
            help="Worker name : example ajp://127.0.0.1:8001", type=str)
ARGS = PARSER.parse_args()

#############################################################################
# default values

host='localhost'
port = 80

if ARGS.host:
    host = ARGS.host
    if ARGS.port: port = ARGS.port

if ARGS.port:
    port = ARGS.port

url="http://%s:%s/jkstatus/" % (host, port)

#############################################################################
# functions

def getWorkersList():

    reqUrl = "%s?cmd=list" % (url)
    req = Request(reqUrl, None)
    f = urlopen(req)

    class LBParser(HTMLParser.HTMLParser):
        def __init__(self):
            self.workers           = {}
            self._wData            = None
            self.datas             = []
            self._tds              = []
            self._balancer         = ''
            self.in_td             = False
            self.in_th             = False
            self.in_h3             = False

            self.in_bm_declaration = False
            self.in_bm_status      = False

            HTMLParser.HTMLParser.__init__(self)

        def handle_starttag(self, tag, attrs):
            if tag == 'td':
                self.in_td = True
            elif tag == 'th':
                self.in_th = True
            elif tag == 'h3':
                self.in_h3 = True
            elif self.in_h3 and not self.in_td and tag == 'a':
                b = self.get_balancer_name(attrs)
                if b:
                    self._balancer = b

        def handle_data(self, data):
            if self.in_td:
                self._tds.append(data)
                self._wData = data
            elif self.in_th and data == 'Address:Port':
                self.in_bm_declaration = True
            elif self.in_th and data == 'Route':
                self.in_bm_status = True

        def handle_endtag(self, tag):

            # if no text data was enclosed by the tag, handle_data function
            # is not called, we have to handle it with a hook
            if self.in_td and self._wData == None:
                self._tds.append('')
                #print "ERROR: %s" % (self.get_starttag_text())
            self._wData = None

            self.in_td = False
            self.in_th = False
            self.in_h3 = False

            if tag == 'table':
                self.in_bm_declaration = False
                self.in_bm_status      = False

            if tag == 'tr':
                if self.in_bm_declaration and self._tds != []:
                    wName = self._tds[0]
                    worker = {}

                    # first workers table
                    worker['Type']                  = self._tds[1]
                    worker['Hostname']              = self._tds[2]
                    worker['Address:Port']          = self._tds[3]
                    worker['ConnectionPoolTimeout'] = self._tds[4]
                    worker['ConnectTimeout']        = self._tds[5]
                    worker['PrepostTimeout']        = self._tds[6]
                    worker['ReplyTimeout']          = self._tds[7]
                    worker['Retries']               = self._tds[8]
                    worker['RecoveryOptions']       = self._tds[9]
                    worker['MaxPacketSize']         = self._tds[10]
                    worker['Balancer']              = self._balancer

                    self.workers[wName] = worker

                elif self.in_bm_status and self._tds != []:
                    if len(self._tds) > 1:
                        # there is a legend table which we do not want to
                        # look in
                        wName = self._tds[2]
                        if self.workers.has_key(wName):
                            # second workers table
                            self.workers[wName]['ActConf']        = self._tds[3]
                            self.workers[wName]['State']          = self._tds[4]
                            self.workers[wName]['Distance']       = self._tds[5]
                            self.workers[wName]['Factor']         = self._tds[6]
                            self.workers[wName]['Multiplicity']   = self._tds[7]
                            self.workers[wName]['Value']          = self._tds[8]
                            self.workers[wName]['ReqNr']          = self._tds[9]
                            self.workers[wName]['SessNr']         = self._tds[10]
                            self.workers[wName]['ErrNr']          = self._tds[11]
                            self.workers[wName]['ClinetErrNr']    = self._tds[12]
                            self.workers[wName]['RyplyTO']        = self._tds[13]
                            self.workers[wName]['BytesWr']        = self._tds[14]
                            self.workers[wName]['BytesRead']      = self._tds[15]
                            self.workers[wName]['BusyConnNr']     = self._tds[16]
                            self.workers[wName]['BusyConnMaxNr']  = self._tds[17]
                            self.workers[wName]['BackendConnNr']  = self._tds[18]
                            self.workers[wName]['Route']          = self._tds[19]
                            self.workers[wName]['RouteRedirect']  = self._tds[20]
                            self.workers[wName]['ClusterDomain']  = self._tds[21]
                            self.workers[wName]['RecoverySched']  = self._tds[22]
                            self.workers[wName]['LastReset']      = self._tds[23]
                            self.workers[wName]['LastErr']        = self._tds[24]
                        else:
                            print "ERROR: could not find worker name in the status table"

                self._tds = []

        def get_balancer_name(self, attrs):
            '''Just a convinience function'''
            for prop, val in attrs:
                if prop == 'href':
                    # extract balancer name from the query string
                    parsed = urlparse.urlparse(val)

                    if parsed.path and parsed.query:
                        r = urlparse.parse_qs(parsed.query)
                        if r.has_key('w'):
                            return r['w'][0]
            return False


    p = LBParser()
    p.feed(f.read())

    return p.workers


def balancer_status():

    workers = getWorkersList()

    if workers:
        template = "{Worker:40} | {Route:16} | {Status:10}| {From:16} | {To:16} | {Balancer:80}"
        # print workers.keys()
        print template.format( Worker="Worker", Route="Route", Status="Status", From='From', To = 'To', Balancer='Balancer' )

        for k in sorted(workers.keys()):
            # print workers[k]
            print template.format(
                Worker   = "%s://%s:%s" % (workers[k]['Type'], workers[k]['Hostname'], workers[k]['Address:Port'].split(':')[1]),
                Route    = workers[k]['Route'],
                Status   = workers[k]['ActConf'],
                From     = workers[k]['BytesRead'],
                To       = workers[k]['BytesWr'],
                Balancer = workers[k]['Balancer']
            )

        return True

    return False

def balancer_manage(sAction, worker):

    if sAction not in ['enable', 'disable']:
        print "Unknown action: %s" %(sAction)
        return False

    workers = getWorkersList()

    found = False
    for k in workers.keys():

        if worker == "%s://%s:%s" % (workers[k]['Type'], workers[k]['Hostname'], workers[k]['Address:Port'].split(':')[1]):
            found = True

            action   = (0,1)[sAction == 'disable']
            balancer = workers[k]['Balancer']

            params = urlencode({'cmd': 'update', 'from': 'list','w': balancer, 'sw': k, 'vwa': action})
            req    = Request(url+"?%s" % params, None)
            urlopen(req)

            print "Action\n    Worker %s [%s]\n\nStatus" % (worker,sAction)
            balancer_status()

    if not found:
        print "Could not find worker: %s" %(worker)
        return False


#############################################################################

r = 0

if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        r = balancer_status()
    elif ARGS.action and ARGS.worker:
        r = balancer_manage(ARGS.action,ARGS.worker)
    else:
        PARSER.print_help()

    sys.exit( not r )
