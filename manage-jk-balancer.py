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
#        worker.appsrvA0.reference=worker.template
#        worker.appsrvA0.host=appa01.e.ol.dvag.com
#        worker.appsrvA0.port=23009
#        worker.appsrvA1.reference=worker.template
#        worker.appsrvA1.host=appa01.e.ol.dvag.com
#        worker.appsrvA1.port=23109
#        worker.appsrvB0.reference=worker.template
#        worker.appsrvB0.host=appa02.e.ol.dvag.com
#        worker.appsrvB0.port=23009
#        worker.appsrvB1.reference=worker.template
#        worker.appsrvB1.host=appa02.e.ol.dvag.com
#        worker.appsrvB1.port=23109
#
#        worker.appsrv.type=lb
#        worker.appsrv.method=B
#        worker.appsrv.recover_time=30
#        worker.appsrv.balance_workers=appsrvA0 appsrvA1 appsrvB0 appsrvB1
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

from urllib  import urlencode
from urllib2 import Request
from urllib2 import urlopen
from urlparse import urlparse

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
    #print f.read()

    class TableParser(HTMLParser.HTMLParser):
        def __init__(self):
            self.datas=[]
            self._tds=[]
            HTMLParser.HTMLParser.__init__(self)
            self.in_td = False

        def handle_starttag(self, tag, attrs):
            if tag == 'td' or tag == 'th' or tag == 'h3':
            #if tag == 'h4':
                self.in_td = True

        def handle_data(self, data):
            if self.in_td:
                self._tds.append(data)

        def handle_endtag(self, tag):
            self.in_td = False
            if tag == 'tr' or tag == 'h3':
                self.datas.append(self._tds)
                self._tds = []


    p = TableParser()
    p.feed(f.read())

    balancer = p.datas[20][0]
    result = re.search("URI Mappings for ([a-zA-Z0-9]+)", balancer)
    if result is not None:
        balancer = result.group(1)
    else:
        print "Could not extract balancer name"
        return 1

    workers  = {}
    for i in p.datas[10:14]: workers[i[0]] = i[1:]
    for i in p.datas[15:19]: workers[i[2]] = workers[i[2]] + i[3:]

    state = {}
    for s in workers.keys():
        #print s, workers[s]
        a = "%s://%s:%s" % (workers[s][0], workers[s][1],workers[s][2].split(':')[1])
        b = ('enabled', 'disabled')[workers[s][10]=='DIS']
        state[s] = [a, b, balancer]

    return state


def balancer_status():

    state = getWorkersList()

    template = "    {Worker:40} | {Status:10}"
    print template.format(Worker="Worker",Status="Status")
    for k in sorted(state.keys()):
        print template.format(Worker=state[k][0],Status=state[k][1])
        template.format(Worker=state[k][0],Status=state[k][1])


def balancer_manage(sAction, worker):

    if sAction not in ['enable', 'disable']:
        print "Unknown action: %s" %(sAction)
        return 1

    state = getWorkersList()

    found = False
    for k in state.keys():

        if state[k][0] == worker:
            found = True

            r = urlparse(state[k][0])
            print r
            if r.scheme:
                # the URL is parsable

                action   = (0,1)[sAction == 'disable']
                balancer = state[k][2]

                params = urlencode({'cmd': 'update', 'from': 'list','w': balancer, 'sw': k, 'vwa': action})
                req    = Request(url+"?%s" % params, None)
                urlopen(req)

                print "Action\n    Worker %s [%s]\n\nStatus" % (worker,sAction)
                balancer_status()
            else:
                print "Could not parse woker URL: %s" %(worker)
                return 1

    if not found:
        print "Could not find worker: %s" %(worker)
        return 1


#############################################################################

if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        balancer_status()
    elif ARGS.action and ARGS.worker:
        r = balancer_manage(ARGS.action,ARGS.worker)
        sys.exit(r)
    else : PARSER.print_help()
