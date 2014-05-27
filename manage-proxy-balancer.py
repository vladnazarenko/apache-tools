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

url="http://%s:%s/balancer-manager" % (host, port)

#############################################################################
# functions

def balancer_status():
    req = Request(url, None)
    f = urlopen(req)
    #print f.read()

    class LBParser(HTMLParser.HTMLParser):
        def __init__(self):
            self.workers=[]
            self._tds=[]
            self._wData = None
            self._balancer=""
            HTMLParser.HTMLParser.__init__(self)
            self.in_td   = False

        def handle_starttag(self, tag, attrs):
            if tag == 'td' or tag == 'th':
                self.in_td = True
            elif self.in_td and tag == 'a':
                self._balancer = self.get_balancer_name(attrs)

        def handle_data(self, data):
            if self.in_td:
                self._tds.append(data.lstrip().rstrip())
                self._wData = data

        def handle_endtag(self, tag):

            # if now text data was enclosed by the tag, handle_data function
            # is not called, we have to handle it with a hook
            if self.in_td and self._wData == None:
                self._tds.append('')
                #print "ERROR: %s" % (self.get_starttag_text())
            self._wData = None

            # the tag is closed
            self.in_td = False

            # try to find the worker status
            found      = False
            if tag == 'tr':
                for index, v in enumerate(self._tds):
                    r = urlparse.urlparse(v)
                    if r.scheme:
                        found = True
                        break

                # the worker status found, init the structure
                if found:
                    worker               = {}
                    worker['Balancer']   = self._balancer
                    worker['URL']        = self._tds[index + 0]
                    worker['Route']      = self._tds[index + 1]
                    worker['RouteRedir'] = self._tds[index + 2]
                    worker['Factor']     = self._tds[index + 3]
                    worker['Set']        = self._tds[index + 4]
                    worker['Status']     = ('enabled','disabled')[ self._tds[index + 5].find('Dis') != -1 ]
                    worker['Elected']    = self._tds[index + 6]
                    worker['To']         = self._tds[index + 7]
                    worker['From']       = self._tds[index + 8]
                    self.workers.append(worker)

                self._tds = []

        def get_balancer_name(self, attrs):
            '''Just a convinience function '''
            for prop, val in attrs:
                if prop == 'href':
                    # b     - balancer name
                    # w     - worker name
                    # nonce - nonce
                    parsed = urlparse.urlparse(val)
                    if parsed.path and parsed.query:
                      return urlparse.parse_qs(parsed.query)['b'][0]
            return 'ERROR'

    p = LBParser()
    p.feed(f.read())

    template = "{Worker:40} | {Route:16} | {Status:10}| {From:8} | {To:8} | {Balancer:80}"
    print template.format(Worker="Worker",Route="Route", Status="Status",From='From', To = 'To', Balancer='Balancer')

    for v in p.workers:
        print template.format(
            Worker   = v['URL'],
            Route    = v['Route'],
            Status   = v['Status'],
            From     = v['From'],
            To       = v['To'],
            Balancer = v['Balancer']
        )

def balancer_manage(sAction, worker):

    if sAction not in ['enable', 'disable']:
        print "Unknown action: %s" %(sAction)
        return 1

    #Read informations
    req = Request(url, None)
    f   = urlopen(req)

    #Find balancer and nonce
    result = re.search("b=([^&]+)&w="+worker+"&nonce=([^\"]+)", f.read())
    if result is not None:
        balancer = result.group(1)
        nonce    = result.group(2)

    #Generate URL
    action = (0,1)[sAction == 'disable']
    params = urlencode({'b': balancer, 'w': worker, 'status_D': action, 'nonce': nonce})
    req    = Request(url+"?%s" % params, None)
    f      = urlopen(req)

    print "Action\n    Worker %s [%s]\n\nStatus" % (worker,sAction)
    balancer_status()


#############################################################################

if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        balancer_status()
    elif ARGS.action and ARGS.worker:
        r = balancer_manage(ARGS.action,ARGS.worker)
        sys.exit(r)
    else : PARSER.print_help()
