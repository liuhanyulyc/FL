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
            data[links[j]] = delay
        
        # Add hosts and switches
        switches = {}
        for l in links:
            #if node not exist, create it
            if not switches.has_key( l[0] ):
                switches[ l[0] ] = self.addSwitch("s%s"%l[0])
            if not switches.has_key( l[1] ):
                switches[ l[1] ] = self.addSwitch("s%s"%l[1])
            #add link of nodes
            self.addLink(switches[l[0]], switches[l[1]], delay="%.2fms"%data[l])

        #create host
        h1 = self.addHost('h1', ip = '10.0.0.1')
        self.addLink(switches[2], h1)
        #nodes to send and receive probe packet

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
