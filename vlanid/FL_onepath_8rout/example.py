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

import random
    
class MyTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self, n=2, **opts):
        Topo.__init__(self, **opts)
        from readtopo import readtopo
        links, monitors, paths, adj_path = readtopo()
        data = {}
        random.seed(16)
        for j in range(len(links)):
            uni_delay = random.uniform(2,5)
            k = random.randint(1,5)
            Lambda = random.uniform(0.1,1)
            delay = random.gammavariate(k,Lambda)+uni_delay
            data[links[j]] = 10.00
        # Add hosts and switches
        switches = {}
        for l in links:
            #if node not exist, create it
            if not switches.has_key( l[0] ):
                switches[ l[0] ] = self.addSwitch("s%s"%l[0])
            if not switches.has_key( l[1] ):
                switches[ l[1] ] = self.addSwitch("s%s"%l[1])
            #add link of nodes
            delay = (int(l[0]) + int(l[1]))%10 + 1
            # loss = (int(l[0]) + int(l[1]))%5 + 1
            # self.addLink(switches[l[0]], switches[l[1]], delay="%.2fms"%delay, loss=loss)
            # print "%2s"%l[0], '->', "%2s"%l[1], "delay:%2s"%delay, "loss:%2s"%loss
            self.addLink(switches[l[0]], switches[l[1]], delay="%.2fms"%data[l])

        #nodes to send and receive probe packet

        switches['r'] = self.addSwitch('r%d'%(len(switches)+1))
        for k in monitors:
            self.addLink(switches[k], switches['r'])

        #create host
        h1 = self.addHost('h1')
        self.addLink(switches['r'], h1)
        
def main():
    "Create network and run simple performance test"
    topo = MyTopo(n=4)
    net = Mininet(topo=topo, build = False, link=TCLink)
    c0 = RemoteController( 'c0', ip='0.0.0.0' )
    net.addController(c0)
    net.start()
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    main()
