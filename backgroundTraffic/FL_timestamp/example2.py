#!/bin/bash/env python
#-*- coding: utf-8 -*-
"""
Simple example of setting network and CPU parameters
NOTE: link params limit BW, add latency, and loss.
There is a high chance that pings WILL fail and that
iperf will hang indefinitely if the TCP handshake fails
to complete.
"""

from mininet.topo import Topo
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import CPULimitedHost, RemoteController
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

from random import random
    
class MyTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self, n=2, **opts):
        Topo.__init__(self, **opts)
        switches = {}
        for i in range(1,5):
            switches[i] = self.addSwitch("s%s"%i)
            self.addHost("h%s"%i)
            self.addLink("s%s"%i,"h%s"%i)
        self.addLink(switches[1], switches[2])
        self.addLink(switches[2], switches[3])
        self.addLink(switches[3], switches[4])
        # self.addLink(switches[4], switches[1])

        # from readtopo import readtopo
        # links, monitors, paths, adj_path = readtopo()

        # # Add hosts and switches
        # switches = {}
        # for l in links:
        #     #if node not exist, create it
        #     if not switches.has_key( l[0] ):
        #         switches[ l[0] ] = self.addSwitch("s%s"%l[0])
        #     if not switches.has_key( l[1] ):
        #         switches[ l[1] ] = self.addSwitch("s%s"%l[1])
        #     #add link of nodes
        #     # delay = (int(l[0]) + int(l[1]))%10 + 1
        #     # self.addLink(switches[l[0]], switches[l[1]], delay="%.2fms"%delay)
        #     self.addLink(switches[l[0]], switches[l[1]])

        #nodes to send and receive probe packet
        # Links = {}
        # switches['r'] = self.addSwitch('r%d'%(len(switches)+1))
        # for k in monitors:
        #     if not Links.has_key(int(k)):
        #         Links[int(k)] = self.addLink(switches[int(k)], switches['r'])

        #create host
        # h1 = self.addHost('h1')
        # self.addLink(switches['r'], h1)
        # h3 = self.addHost('h3', ip ='10.0.0.3',mac = '00:00:00:00:00:03')
        # self.addLink(switches['r'], h3)


#         for p in paths:
#             if not Links.has_key(int(p[-2])):
#                 Links[int(p[-2])] = self.addLink(switches[int(p[-2])], switches['r'])
#         #nodes to send and receive probe packet
# #-------------------------------------从这里开始，420----------------------------------------

#         '''switches['r'] = self.addSwitch('r%d'%(len(switches)+1))
#         for k in monitors:
#             self.addLink(switches[k], switches['r'])

#         #create host
#         h1 = self.addHost('h1')
#         self.addLink(switches['r'], h1)'''
        # mmm=1
        # host = {}
        # for i in range(len(switches)):
        #     if not host.has_key(mmm):
        #         host[mmm]=self.addHost('g%d'%mmm)
        #         self.addLink(host[mmm],switches[mmm])
        #         mmm=mmm+1
        
#--------------------------------------到这里结束420-------------------------------------------

def main():
    "Create network and run simple performance test"
    topo = MyTopo(n=4)
    net = Mininet(topo=topo, build = False, link=TCLink)
    c0 = RemoteController( 'c0', controller=RemoteController, ip='0.0.0.0' ,port = 6633)
    net.addController(c0)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    main()
