#!/usr/bin/env python
#-*- coding: utf-8 -*-


# Echo client program
import socket
import json

from collections import defaultdict
import time
import random
import matplotlib.pyplot as plt
import thread
from collections import namedtuple
import sys

Link = namedtuple("Link", "delay loss delay_list loss_list")
connections = {}
cmd = {}
adj = defaultdict(lambda:defaultdict(lambda:None))

def readtopo():
    table = defaultdict(lambda:defaultdict(lambda:None))
    for i in range(5):
        i = i+1
        for p in range(4):
            p = p + 1
            table['192.168.1.11%s'%i]['%s'%p] = 'eth%s'%(p-1)
    table['192.168.1.116'] ={'1':'eth3', '2':'eth0', '3':'eth1', '4':'eth2'}
    link = {}
    with open("topo.txt", "r") as f:
        # i = 0
        for line in f:
            l = line.split()
            adj['192.168.1.11%s'%l[0]]['192.168.1.11%s'%l[1]] = table['192.168.1.11%s'%l[0]][l[2]]
            link[('192.168.1.11%s'%l[0], '192.168.1.11%s'%l[1])] = (int(l[0]), int(l[1]))
                # i += 1
    return link

class Connect(object):
    """docstring for Connect"""

    def __init__(self, host = None, port = 50007):
        super(Connect, self).__init__()
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(2)
        self.Buffer_size = 10240

    def excute(self, string):
        print "%s excute %s"%(self.host, string)
        self.socket.sendto(string, (self.host, self.port))
        try:
            ans = self.socket.recvfrom(self.Buffer_size)
        except:
            ans = {}
            ans['results'] = "%s no answer"%self.host
            ans['status'] = -1
            return ans
        return json.loads(ans[0])

    def __del__(self):
        self.socket.close()

    def __str__(self):
        return self.host

def connect_host(arg):
    host = arg[0]
    connections[host] = Connect(host = host)

def cd(arg):
    if arg[0] not in connections:
        connect_host(arg)
    host = connections[arg[0]]
    while 1:
        try:
            string = raw_input("%s>"%host)
        except EOFError:
            break
        if string == '':
            continue
        ans = host.excute(string)
        print ans['results']
    print "\n",

def link_config(arg):
    # global adj
    host1 = arg[0]
    host2 = arg[1]
    if adj[host1][host2] == None or adj[host2][host1] ==None:
        print "link don't exist"
        try:
            string = raw_input('show link ?[Y]/N')
        except EOFError:
            return
        if string == "Y" or string == '':
            for k in adj:
                for j in adj[k]:
                    if adj[k][j]:
                        print k, j
        return
    if host1 not in connections:
        connect_host([host1])
    if host2 not in connections:
        connect_host([host2])
    command = "tc qdisc change dev %s root netem delay %s loss %s"
    ans = connections[host1].excute(command%(adj[host1][host2], arg[3], arg[5]))
    while(ans['status'] != 0 and ans['status'] != '0'):
        ans = connections[host1].excute(command%(adj[host1][host2], arg[3], arg[5]))
    
    ans = connections[host2].excute(command%(adj[host2][host1], arg[3], arg[5]))
    while(ans['status'] != 0 and ans['status'] != '0'):
        ans = connections[host2].excute(command%(adj[host2][host1], arg[3], arg[5]))

def show_help(arg):
    if not arg:
        print cmd.keys()
    elif arg[0] == 'connect':
        print "connect 127.0.0.1"

    elif arg[0] == 'link_config':
        print "link 12.25.23.4 12.58.69.6 delay 10ms loss 3%"
    
cmd = {'con':connect_host,'link':link_config, 'help':show_help, 'cd':cd}

def config_delay():
    import pickle
    import matplotlib.pyplot as plt
    with open("data.pkl", "r") as f:
        y = {}
        data = pickle.load(f)
        for k in data:
            y[k] = data[k].delay_list
    #         plt.plot(y[k])
    # plt.show()
    return y

def config_loss():
    import pickle
    import matplotlib.pyplot as plt
    with open("data.pkl", "r") as f:
        y = {}
        data = pickle.load(f)
        for k in data:
            y[k] = data[k].loss_list
    #         plt.plot(y[k], '*-')
    # plt.show()
    return y

def main(action = "manual"):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    string = ''
    link = readtopo()
    delay = config_delay()
    loss = config_loss()
    if action == "manual":
        while(True):
            try:
                string = raw_input('ant>')
            except EOFError:
                break
            string_list = string.split()
            if string_list and string_list[0] not in cmd:
                print "I don't understand your meaning. Try help."
            elif string_list:
                cmd[string_list[0]](string_list[1:])
    else:
        log = open(r'%s.log'%time.strftime("%Y_%m_%d_%H:%M:%S"), "w")
        def function_quenue(message_quen):
            for string_list in message_quen:
                cmd[string_list[0]](string_list[1:])
            print "finish"
        for i in range(6):
            print >>log, time.strftime("%H:%M:%S")
            message_quen = []
            for l in link.keys():
                if link[l] not in delay:
                    continue
                string = "link %s %s delay %.2lfms loss %.2lf%%"%(l[0], l[1], delay[link[l]][i], loss[link[l]][i])
                print >> log, string
                string_list = string.split()
                if string_list and string_list[0] not in cmd:
                    print >> log, "I don't understand your meaning. Try help."
                    print >> log, string
                elif string_list:
                    # start a new thread to excute command
                    # thread.start_new_thread(cmd[string_list[0]], (string_list[1:],))
                    message_quen.append(string_list)
                    # cmd[string_list[0]](string_list[1:])
                    pass
            thread.start_new_thread(function_quenue, (message_quen, ))
            log.flush()
            time.sleep(600)
        log.close()
    for k in connections:
        connections[k].socket.close()
    print "\n",
if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        main("auto")
    else:
        main()
