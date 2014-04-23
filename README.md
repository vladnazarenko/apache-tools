apache-tools
===========

Scripts Apache

##Dependency
```bash
   apt-get install python-argparse
   yum     install python-argparse
```

##manage-proxy-balancer.py

 Allows you to manage Worker/BalancerMember defined in your apache2 mod_proxy conf :

```bash
    <Proxy balancer://tomcatservers>
        BalancerMember ajp://10.152.45.1:8001 route=web1 retry=60
        BalancerMember ajp://10.152.45.2:8001 route=web2 retry=60
    </Proxy>
```

You have to allow /balancer-manager
Like :
```bash
 #RewriteCond %{REQUEST_URI} !=/balancer-manager
 ProxyPass /balancer-manager !
 <Location /balancer-manager>
   SetHandler balancer-manager
   Order Deny,Allow
   Deny from all
   Allow from 127.0.0.1
 </Location>
```
##Example of use:
### JK Balancer
```bash
  ./manage-jk-balancer.py -l
  ./manage-jk-balancer.py -w ajp://10.152.45.1:8001 -a enable
```
##manage-jk-balancer.py
 Allows you to manage Worker/BalancerMember defined in your apache2 mod_proxy conf :

```bash
        JkWorkersFile /etc/httpd/conf.d/workers.properties
        JkLogFile "| /usr/sbin/rotatelogs -l /var/log/httpd/mod_jk-%Y-%m-%d.%H.log 3600"
        JkLogLevel error
        JkLogStampFormat "[%a %b %d %H:%M:%S %Y]"
        JkOptions +ForwardKeySize -ForwardDirectories +ForwardURICompatUnparsed
        JkShmFile [PATH]../jk.shm
        JkMount /jkstatus/* status
        JkMount /* [BALANCER NAME]
```

```bash
        worker.status.type=status

        worker.template.type=ajp13
        worker.template.socket_timeout=180
        worker.template.socket_connect_timeout=5000
        worker.template.retries=2
        worker.template.recovery_options=3
        worker.template.distance=0

        worker.appsrvA0.reference=worker.template
        worker.appsrvA0.host=appa01.e.ol.dvag.com
        worker.appsrvA0.port=23009
        worker.appsrvA1.reference=worker.template
        worker.appsrvA1.host=appa01.e.ol.dvag.com
        worker.appsrvA1.port=23109
        worker.appsrvB0.reference=worker.template
        worker.appsrvB0.host=appa02.e.ol.dvag.com
        worker.appsrvB0.port=23009
        worker.appsrvB1.reference=worker.template
        worker.appsrvB1.host=appa02.e.ol.dvag.com
        worker.appsrvB1.port=23109

        worker.appsrv.type=lb
        worker.appsrv.method=B
        worker.appsrv.recover_time=30
        worker.appsrv.balance_workers=appsrvA0 appsrvA1 appsrvB0 appsrvB1

        worker.list=status appsrv
```
 You have to allow /jkstatus
```bash
        <Location /jkstatus>
                Order deny,allow
                Deny from all
                Allow from localhost 127.0.0.1
        </Location>
```

##Example of use:
### Proxy Balancer
```bash
  ./manage-proxy-balancer.py -l
  ./manage-proxy-balancer.py -w ajp://10.152.45.1:8001 -a enable
```
