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
from urllib import urlencode
from urllib2 import Request, urlopen

# Get args
PARSER = argparse.ArgumentParser()
PARSER.add_argument("-l", "--list",
            help="List Worker member and status", action='store_true')
PARSER.add_argument("-a", "--action",
            help="\"enable\" or \"disable\" the specified Worker", type=str)
PARSER.add_argument("-w", "--worker",
            help="Worker name : example ajp://127.0.0.1:8001", type=str)
ARGS = PARSER.parse_args()

#Fix if necessary
#vhostname
headers = {"Host": '127.0.0.1' }
#ip to reach apache
url="http://127.0.0.1/balancer-manager"

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
    for v in p.datas[2:]:
        print template.format(Worker=v[0],Status=v[3].split(" ")[1],Elected=v[4], To=v[5], From=v[6])


def balancer_manage(action, worker):
    #Read informations
    req = Request(url, None, headers)
    f = urlopen(req)

    #Find balancer and nonce
    result = re.search("b=([^&]+)&w="+worker+"&nonce=([^\"]+)", f.read())
    if result is not None:
        balancer = result.group(1)
        nonce = result.group(2)
    #Generate URL
    action = (0,1)[action == 'disable']
    params = urlencode({'b': balancer, 'w': worker, 'status_D': action, 'nonce': nonce})
    req = Request(url+"?%s" % params, None, headers)
    f = urlopen(req)
    print "Action\n    Worker %s [%s]\n\nStatus" % (worker,action)
    balancer_status()



if __name__ == "__main__":
    #if ARGS.list is not None:
    if ARGS.list :
        balancer_status()
    elif ARGS.action and ARGS.worker:
        balancer_manage(ARGS.action,ARGS.worker)
    else : PARSER.print_help()
