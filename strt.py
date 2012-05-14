#!/usr/bin/python
# -*- coding: utf8 -*-

import os
import sys
import time
import subprocess as sp
from pwd import getpwnam

# Set the destination directories for openstack projects
SERVICE_TIMEOUT = 60
DEST = "/opt/stack"

#trying to execute something from console, using bash.
#text = getoutput('bash -c ls')

#Функция 
def screen_it(s_name,cmd):
    sp.call('screen -S stack -X screen -t %s'%(s_name,), shell= True)
    sp.call('screen -S stack -p %s -X stuff "%s\n\r"'%(s_name, cmd), shell= True)
#Небольшая магия для совместимости с 2.6.6
def check_output(stroka, shell=True):
        ret = sp.Popen(stroka, shell= shell, stdout=sp.PIPE).communicate()[0]
        return ret, None
#Переопределение имени
sp.check_output = check_output

#тащим установленные сервисы
localrc = open('/opt/stack/devstack/localrc','r')
for line in localrc: 
    if "ENABLED_SERVICES" in line:
        ENABLED_SERVICES = line.split("=")[1]
        break
print ENABLED_SERVICES
# Стартовать мы должны все из под пользователя stack. Поэтому нада сделать su.

# Тащим UID для пользователя stack
stack_uid=getpwnam('stack').pw_uid
stack_gid=getpwnam('stack').pw_gid

#небольшая магия, против тех кто бездумно юзает chown. нужна очень очень :)
os.system('chown -R %s:%s %s'%(stack_uid, stack_gid, DEST))

#А теперь все делаем только из под пользователя stack
cur_uid = os.getuid()

if cur_uid != stack_uid and cur_uid == 0:
    os.setuid(int(stack_uid))
    myname = sp.check_output('whoami', shell= True)
    print "Running under: ", myname
    os.chdir('/opt/stack')
    #print sp.check_output('pwd', shell= True)
else:
    print "Please run this script with \"root\" or \"stack\" privilegies. Exiting. .",
    time.sleep(1)
    print ".",
    time.sleep(1)
    print ".",
    time.sleep(1)
    print ".",
    sys.exit()

# Kill stack screen
os.system('screen -r stack -X quit')

# Нам все нужно запускать в скрине, поэтому создаем его.
screen_out = os.system('screen -d -m -S stack -t stack && screen -r stack -X hardstatus alwayslastline "%-Lw%{= BW}%50>%n%f* %t%{-}%+Lw%< %= %H"')
if screen_out == 0:
    print "Screen has been created"
else:
    print "Screen hasn't been created"

# launch the glance registry service
if "g-reg" in ENABLED_SERVICES:
    screen_it("g-reg", "cd /opt/stack/glance; bin/glance-registry --config-file=/etc/glance/glance-registry.conf")

# launch the glance api and wait for it to answer before continuing
if "g-api" in ENABLED_SERVICES:
    screen_it("g-api","cd /opt/stack/glance; bin/glance-api --config-file=/etc/glance/glance-api.conf") 
    time.sleep(3)
    print "Waiting for g-api to start..."
    try:
        strt_results = sp.check_output('wget -q -O- http://127.0.0.1:9292', shell= True)
    except sp.CalledProcessError as exc:
        if exc.returncode != 4:
            raise
        else:
            strt_results = ''
    if  strt_results == '':
        print "g-api did not start"
    else:
        print "G-api has been started successful"

# launch the keystone and wait for it to answer before continuing
if "key" in ENABLED_SERVICES:
    screen_it("key","cd /opt/stack/keystone && /opt/stack/keystone/bin/keystone-all --config-file /etc/keystone/keystone.conf --log-config /etc/keystone/logging.conf -d --debug")
    print "Waiting for keystone to start..."
    try:
        strt_results = sp.check_output('wget -q -O- http://127.0.0.1:5000', shell= True)
    except sp.CalledProcessError as exc:
        if exc.returncode != 4:
            raise
        else:
            strt_results = ''
    if  strt_results == '':
        print "keystone did not start"
    else:
        print "keystone has been started successful"


# launch the nova-api and wait for it to answer before continuing
if "n-api" in ENABLED_SERVICES:
    screen_it("n-api","cd /opt/stack/nova && /opt/stack/nova/bin/nova-api")
    print "Waiting for nova-api to start..."
    try:
        strt_results = sp.check_output('wget -q -O- http://127.0.0.1:8774', shell= True)
    except sp.CalledProcessError as exc:
        if exc.returncode != 4:
            raise
        else:
            strt_results = ''
    if  strt_results == '':
        print "n-api did not start"
    else:
        print "n-api has been started successful"


if "n-cpu" in ENABLED_SERVICES:
    screen_it("n-cpu","cd /opt/stack/nova && sudo sg libvirtd /opt/stack/nova/bin/nova-compute")
if "n-vol" in ENABLED_SERVICES:
    screen_it("n-vol","sudo losetup -f /opt/stack/nova-volumes-backing-file; cd /opt/stack/nova && /opt/stack/nova/bin/nova-volume")
if "n-net" in ENABLED_SERVICES:
    screen_it("n-net","sudo ip addr del 169.254.169.254/32 scope link dev lo; cd /opt/stack/nova && /opt/stack/nova/bin/nova-network")
if "n-sch" in ENABLED_SERVICES:
    screen_it("n-sch","cd /opt/stack/nova && /opt/stack/nova/bin/nova-scheduler")
if "n-vnc" in ENABLED_SERVICES:
    screen_it("n-vnc","cd /opt/stack/noVNC && ./utils/nova-novncproxy --config-file /etc/nova/nova.conf --web .")
if "n-cauth" in ENABLED_SERVICES:
    screen_it("n-cauth","cd /opt/stack/nova/ && ./bin/nova-consoleauth")
if "n-xvnc" in ENABLED_SERVICES:
    screen_it("n-xvnc","cd /opt/stack/nova && ./bin/nova-xvpvncproxy --config-file /etc/nova/nova.conf")
if "n-novnc" in ENABLED_SERVICES:
    screen_it("n-novnc","cd /opt/stack/noVNC && ./utils/nova-novncproxy --config-file /etc/nova/nova.conf --web .")
if "n-obj" in ENABLED_SERVICES:
    screen_it("n-obj","cd /opt/stack/nova && /opt/stack/nova/bin/nova-objectstore")
if "n-crt" in ENABLED_SERVICES:
    screen_it("n-crt","cd /opt/stack/nova && /opt/stack/nova/bin/nova-cert") 
if "swift" in ENABLED_SERVICES:
 sp.call("sudo mount -t xfs -o loop,noatime,nodiratime,nobarrier,logbufs=8 /opt/stack/data/swift/drives/images/swift.img /opt/stack/data/swift/drives/sdb1/; sudo swift-init all restart", shell=True)
if "horizon" in ENABLED_SERVICES:
    screen_it("horizon","cd /opt/stack/horizon && sudo tail -f /var/log/httpd/horizon_error.log")
if "llapi" in ENABLED_SERVICES:
    screen_it("llapi","cd /opt/jade/low_level_api && sudo python manage.py runserver 0.0.0.0:8187")

