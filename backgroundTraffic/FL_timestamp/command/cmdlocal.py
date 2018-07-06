#!/usr/bin/env python
#-*- coding: utf-8 -*-

import commands
from collections import defaultdict, namedtuple
import pickle
import matplotlib.pyplot as plt
import time


Link = namedtuple("Link", "delay delay_list")
adj = defaultdict(lambda:defaultdict(lambda:None))
link = {}

def init_adj():
    with open("topo_local.txt", "r") as f:
        i = 0
        for line in f:
            l = line.split()
            adj[int(l[0])][int(l[1])] = l[2]
            link[(int(l[0]), int(l[1]))] = (int(l[0]), int(l[1]))

def config_delay():
    with open("data.pkl", "r") as f:
        y = {}
        data = pickle.load(f)
        # print data
        for k in data:
            y[k] = data[k].delay_list
    #         plt.plot(y[k])
    # plt.show()
    return y

def command_delay(port1, port2, delay, action = "change"):
    ans = {}
    string = "tc qdisc %s dev s%s-eth%s root netem delay %sms"\
                    %(action, port1, adj[port1][port2], delay)
    print string
    ans['status'], ans['results'] = commands.getstatusoutput(string)
    # /usr/lib/python2.7/commands.py
    if ans['status']:
        print ans['results'], string
    string = "tc qdisc %s dev s%s-eth%s root netem delay %sms"\
                    %(action, port2, adj[port2][port1], delay)
    print string 
    ans['status'], ans['results'] = commands.getstatusoutput(string)
    if ans['status']:
        print ans['results'], string

def main():
    init_adj()
    delay = config_delay()
    with open("delay_list.txt", "w") as f:
        for i in range(200):
            f.write('time:')
            f.write("\n")
            f.write(str(time.time()))
            f.write("\n")
            for k in link:
                if link[k] not in delay:
                    continue
                command_delay(k[0], k[1], delay[link[k]][i])
                f.write(str(str(k[0]) + ' '))
                f.write(str(str(k[1]) + ' '))
                f.write(str(delay[link[k]][i]))
                f.write("\n")
            f.write("\n")
            time.sleep(0.25)
if __name__ == '__main__':
    main()
