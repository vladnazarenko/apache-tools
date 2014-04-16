#!/usr/bin/python -O
#
# Author: Florian Lambert <florian.lambert@enovance.com>
# Source: https://github.com/talset/apache-tools
#
# Allow you to manage Worker/BalancerMember defined in your apache2 mod_proxy conf :
#    <Proxy balancer://tomcatservers>
#        BalancerMember ajp://10.152.45.1:8001 route=web1 retry=60
#        BalancerMember ajp://10.152.45.2:8001 route=web2 retry=60
#    </Proxy>
#
# You have to allow /balancer-manager
#Like :
# ProxyPass /balancer-manager !
# <Location /balancer-manager>
#   SetHandler balancer-manager
#   Order Deny,Allow
#   Deny from all
#   Allow from 127.0.0.1
# </Location>
#
# Verify url="http....."
#
#
# HOW TO :
#   balancer-manager.py -l
#   balancer-manager.py -w ajp://10.152.45.1:8001 -a enable
#
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

url="http://%s:%s/balancer-manager" % (host, port)

#############################################################################
# functions

def balancer_status():
    req = Request(url, None, headers)
    f = urlopen(req)
    #print f.read()

    class TableParser(HTMLParser.HTMLParser):
        def __init__(self):
            self.datas=[]
            self._tds=[]
            HTMLParser.HTMLParser.__init__(self)
            self.in_td = False

        def handle_starttag(self, tag, attrs):
            if tag == 'td' or tag == 'th':
                self.in_td = True

        def handle_data(self, data):
            if self.in_td:
                self._tds.append(data)

        def handle_endtag(self, tag):
            self.in_td = False
            if tag == 'tr':
                self.datas.append(self._tds)
                self._tds = []

    p = TableParser()
    p.feed(f.read())

    template = "    {Worker:40} | {Status:10} | {Elected:10} | {To:10} | {From:10}"

    print template.format(Worker="Worker",Status="Status",Elected="Elected", To="To", From="From")
    for v in p.datas:
        r = urlparse(v[0])
        if r.scheme:
            # the URL is parsable
            print template.format(Worker=v[0],Status=v[3],Elected=v[4], To=v[5], From=v[6])
            template.format(Worker=v[0],Status=v[3],Elected=v[4], To=v[5], From=v[6])


def balancer_manage(sAction, worker):

    if sAction not in ['enable', 'disable']:
        print "Unknown action: %s" %(sAction)
        return 1

    #Read informations
    req = Request(url, None, headers)
    f = urlopen(req)

    #Find balancer and nonce
    result = re.search("b=([^&]+)&w="+worker+"&nonce=([^\"]+)", f.read())
    if result is not None:
        balancer = result.group(1)
        nonce = result.group(2)
    #Generate URL
    action = (0,1)[sAction == 'disable']
    params = urlencode({'b': balancer, 'w': worker, 'status_D': action, 'nonce': nonce})
    req = Request(url+"?%s" % params, None, headers)
    f = urlopen(req)
    print "Action\n    Worker %s [%s]\n\nStatus" % (worker,sAction)
    balancer_status()



if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        balancer_status()
    elif ARGS.action and ARGS.worker:
        r = balancer_manage(ARGS.action,ARGS.worker)
        sys.exit(r)
    else : PARSER.print_help()
