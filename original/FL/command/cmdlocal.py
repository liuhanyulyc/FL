#!/usr/bin/env python
#-*- coding: utf-8 -*-

import commands
from collections import defaultdict, namedtuple
import pickle
import matplotlib.pyplot as plt
import time


Link = namedtuple("Link", "delay loss delay_list loss_list")
adj = defaultdict(lambda:defaultdict(lambda:None))
link = {}

def init_adj():
    with open("topo_local.txt", "r") as f:
        i = 0
        for line in f:
            l = line.split()
            adj[l[0]][l[1]] = l[2]
            link[(l[0], l[1])] = (int(l[0]), int(l[1]))
def config_delay():
    with open("data.pkl", "r") as f:
        y = {}
        data = pickle.load(f)
        for k in data:
            y[k] = data[k].delay_list
    #         plt.plot(y[k])
    # plt.show()
    return y

def config_loss():
    with open("data.pkl", "r") as f:
        y = {}
        data = pickle.load(f)
        for k in data:
            y[k] = data[k].loss_list
    #         plt.plot(y[k], '*-')
    # plt.show()
    return y

def command_delay_loss(port1, port2, delay, loss, action = "change"):
    ans = {}
    string = "tc qdisc %s dev s%s-eth%s root netem delay %sms loss %s%%"\
                    %(action, port1, adj[port1][port2], delay, loss)
    print string
    ans['status'], ans['results'] = commands.getstatusoutput(string)
    if ans['status']:
        print ans['results'], string
    string = "tc qdisc %s dev s%s-eth%s root netem delay %sms loss %s%%"\
                    %(action, port2, adj[port2][port1], delay, loss)   
    print string 
    ans['status'], ans['results'] = commands.getstatusoutput(string)
    if ans['status']:
        print ans['results'], string

def main():
    init_adj()
    delay = config_delay()
    loss = config_loss()
    for i in range(6):
        for k in link:
            if link[k] not in delay:
                continue
            command_delay_loss(k[0], k[1], delay[link[k]][i], loss[link[k]][i])
        time.sleep(10)
if __name__ == '__main__':
    main()
