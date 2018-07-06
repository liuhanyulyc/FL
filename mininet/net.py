"""

    Mininet: A simple networking testbed for OpenFlow/SDN!

author: Bob Lantz (rlantz@cs.stanford.edu)
author: Brandon Heller (brandonh@stanford.edu)

Mininet creates scalable OpenFlow test networks by using
process-based virtualization and network namespaces.

Simulated hosts are created as processes in separate network
namespaces. This allows a complete OpenFlow network to be simulated on
top of a single Linux kernel.

Each host has:

A virtual console (pipes to a shell)
A virtual interfaces (half of a veth pair)
A parent shell (and possibly some child processes) in a namespace

Hosts have a network interface which is configured via ifconfig/ip
link/etc.

This version supports both the kernel and user space datapaths
from the OpenFlow reference implementation (openflowswitch.org)
as well as OpenVSwitch (openvswitch.org.)

In kernel datapath mode, the controller and switches are simply
processes in the root namespace.

Kernel OpenFlow datapaths are instantiated using dpctl(8), and are
attached to the one side of a veth pair; the other side resides in the
host namespace. In this mode, switch processes can simply connect to the
controller via the loopback interface.

In user datapath mode, the controller and switches can be full-service
nodes that live in their own network namespaces and have management
interfaces and IP addresses on a control network (e.g. 192.168.123.1,
currently routed although it could be bridged.)

In addition to a management interface, user mode switches also have
several switch interfaces, halves of veth pairs whose other halves
reside in the host nodes that the switches are connected to.

Consistent, straightforward naming is important in order to easily
identify hosts, switches and controllers, both from the CLI and
from program code. Interfaces are named to make it easy to identify
which interfaces belong to which node.

The basic naming scheme is as follows:

    Host nodes are named h1-hN
    Switch nodes are named s1-sN
    Controller nodes are named c0-cN
    Interfaces are named {nodename}-eth0 .. {nodename}-ethN

Note: If the network topology is created using mininet.topo, then
node numbers are unique among hosts and switches (e.g. we have
h1..hN and SN..SN+M) and also correspond to their default IP addresses
of 10.x.y.z/8 where x.y.z is the base-256 representation of N for
hN. This mapping allows easy determination of a node's IP
address from its name, e.g. h1 -> 10.0.0.1, h257 -> 10.0.1.1.

Note also that 10.0.0.1 can often be written as 10.1 for short, e.g.
"ping 10.1" is equivalent to "ping 10.0.0.1".

Currently we wrap the entire network in a 'mininet' object, which
constructs a simulated network based on a network topology created
using a topology object (e.g. LinearTopo) from mininet.topo or
mininet.topolib, and a Controller which the switches will connect
to. Several configuration options are provided for functions such as
automatically setting MAC addresses, populating the ARP table, or
even running a set of terminals to allow direct interaction with nodes.

After the network is created, it can be started using start(), and a
variety of useful tasks maybe performed, including basic connectivity
and bandwidth tests and running the mininet CLI.

Once the network is up and running, test code can easily get access
to host and switch objects which can then be used for arbitrary
experiments, typically involving running a series of commands on the
hosts.

After all desired tests or activities have been completed, the stop()
method may be called to shut down the network.

"""

import os
import re
import select
import signal
import random

from time import sleep
from itertools import chain, groupby
from math import ceil

from mininet.cli import CLI
from mininet.log import info, error, debug, output, warn
from mininet.node import ( Node, Host, OVSKernelSwitch, DefaultController,
                           Controller )
from mininet.nodelib import NAT
from mininet.link import Link, Intf
from mininet.util import ( quietRun, fixLimits, numCores, ensureRoot,
                           macColonHex, ipStr, ipParse, netParse, ipAdd,
                           waitListening )
from mininet.term import cleanUpScreens, makeTerms

# Mininet version: should be consistent with README and LICENSE
VERSION = "2.3.0d1"

class Mininet( object ):
    "Network emulation with hosts spawned in network namespaces."

    def __init__( self, topo=None, switch=OVSKernelSwitch, host=Host,
                  controller=DefaultController, link=Link, intf=Intf,
                  build=True, xterms=False, cleanup=False, ipBase='10.0.0.0/8',
                  inNamespace=False,
                  autoSetMacs=False, autoStaticArp=False, autoPinCpus=False,
                  listenPort=None, waitConnected=False ):
        """Create Mininet object.
           topo: Topo (topology) object or None
           switch: default Switch class
           host: default Host class/constructor
           controller: default Controller class/constructor
           link: default Link class/constructor
           intf: default Intf class/constructor
           ipBase: base IP address for hosts,
           build: build now from topo?
           xterms: if build now, spawn xterms?
           cleanup: if build now, cleanup before creating?
           inNamespace: spawn switches and controller in net namespaces?
           autoSetMacs: set MAC addrs automatically like IP addresses?
           autoStaticArp: set all-pairs static MAC addrs?
           autoPinCpus: pin hosts to (real) cores (requires CPULimitedHost)?
           listenPort: base listening port to open; will be incremented for
               each additional switch in the net if inNamespace=False"""
        self.topo = topo
        self.switch = switch
        self.host = host
        self.controller = controller
        self.link = link
        self.intf = intf
        self.ipBase = ipBase
        self.ipBaseNum, self.prefixLen = netParse( self.ipBase )
        hostIP = ( 0xffffffff >> self.prefixLen ) & self.ipBaseNum
        # Start for address allocation
        self.nextIP = hostIP if hostIP > 0 else 1
        self.inNamespace = inNamespace
        self.xterms = xterms
        self.cleanup = cleanup
        self.autoSetMacs = autoSetMacs
        self.autoStaticArp = autoStaticArp
        self.autoPinCpus = autoPinCpus
        self.numCores = numCores()
        self.nextCore = 0  # next core for pinning hosts to CPUs
        self.listenPort = listenPort
        self.waitConn = waitConnected

        self.hosts = []
        self.switches = []
        self.controllers = []
        self.links = []

        self.nameToNode = {}  # name to Node (Host/Switch) objects

        self.terms = []  # list of spawned xterm processes

        Mininet.init()  # Initialize Mininet if necessary

        self.built = False
        if topo and build:
            self.build()
#.....................................add...................................
    def iperf_single( self,hosts=None, udpBw='10M', period=60, port=5001):
        """Run iperf between two hosts using UDP.
           hosts: list of hosts; if None, uses opposite hosts
           returns: results two-element array of server and client speeds"""
        if not hosts:
            return
        else:
            assert len( hosts ) == 2
        client, server = hosts
        filename = client.name + server.name + '.txt'
        print client.name
        print client.IP()
        output( '*** Iperf: testing bandwidth between ' )
        output( "%s and %s\n" % ( client.name, server.name ) )
        iperfArgs = 'iperf -u '
        bwArgs = '-b ' + udpBw + ' '
        print udpBw
        print "***start server***"
        server.cmd( iperfArgs + '-s -i 1 -p ' + str(port) +' > /home/liu/log/' + filename + '&')
        # server.cmd( iperfArgs + '-s -i 1 -p ' + str(port) + '&')

        print "***start client***"
        client.cmd(
            iperfArgs + '-t '+ str(period) + ' -p' + str(port) +' -c ' + server.IP() + ' ' + bwArgs
            +' > /home/liu/log/' + 'client' + filename +'&')
        # client.cmd(
            # iperfArgs + '-t '+ str(period) + ' -p' + str(port) +' -c ' + server.IP() + ' ' + bwArgs+ '&')

    def iperfMulti(self, period=80, lambda_time = 1.0):
        base_port = 5001
        server_list = []
        client_list = [h for h in self.hosts]
        host_list = []
        host_list = [h for h in self.hosts]
        flow_float=[0.0, 10.116288899999999, 61.44146665, 12.69936445, 162.5809511, 6.520982200000001, 8.406524450000001, 93.51126665000001, 182.76211554999998, 0.0, 2.54555555, 16.9617911, 0.60656, 3.82112, 1.2786222, 9.0232222, 13.2792489, 8.800057800000001, 3.8807822, 0.2498089, 9.3778622, 2.53822665, 0.08088, 7.071142200000001, 0.0, 3.12630665, 66.28167555, 0.75585335, 6.139964450000001, 7.53691555, 0.7647999999999999, 1.0020489, 0.0, 4.867306650000001, 89.0618711, 7.2237689, 1.0403378, 0.5598933500000001, 6.38633335, 37.54480445, 90.4095778, 1.3173822, 0.6683778, 3.44938665, 3.2020711, 0.00787555, 20.739564450000003, 6.3820489, 0.0, 43.5005378, 2.28710665, 0.013995549999999999, 1.3263733500000001, 0.14616445, 0.2934978, 0.0, 112.7962622, 10.28328445, 2.63948445, 35.7664089, 0.03324, 0.99354665, 6.86990665, 120.37853335, 1.0773822, 2.18233335, 9.063422200000002, 1.1141422, 0.1010622, 2.6204533499999996, 37.0289822, 15.69784445, 0.0, 1.58233335, 0.0376, 48.668191099999994, 1.1415911, 5.5364889, 0.0, 3.89472, 15.615879999999999, 0.0, 1.4185111, 0.4344222, 2.39755555, 55.605035550000004, 2.4588, 8.0031689, 1.0440444500000001, 13.383635550000001, 4.37371555, 0.00179555, 0.0606222, 99.8665111, 0.43346665, 5.062875549999999, 0.0, 0.01875555, 0.33217779999999997, 7.42618665, 1.2088311, 0.0, 2.5849644499999997, 232.11287109999998, 5.537288899999999, 0.06519554999999999, 1.65551555, 0.60047555, 59.427733350000004, 0.42149335000000004, 0.37327999999999995, 4.5385378, 0.74776445, 3.6640222, 0.0073422, 0.043911099999999995, 1.1518578, 0.11797334999999999, 0.09644889999999999, 0.00044445, 0.0, 0.3221422, 0.00035555, 0.00372, 0.0, 0.08684444999999999, 7.028631099999999, 0.01932, 0.0, 0.0, 0.010199999999999999, 0.85783555, 0.0176622, 0.05461335, 0.00044445, 0.07512, 0.030253350000000002, 0.019093350000000002, 3.6045822, 10.8848311, 5.68032445, 15.7406311, 1.3041289, 0.026546649999999998, 0.0, 0.9361066499999999, 0.8449911, 0.0, 1.86776, 6.663279999999999, 0.6856978, 2.3737022000000003, 0.3385289, 1.0679022, 8.3862222, 0.46017335000000004, 1.4132711, 4.75372, 18.026946650000003, 1.9323511, 0.32030664999999997, 0.14159110000000003, 81.08363555000001, 1.32588445, 5.00758665, 3.8961778, 0.02299555, 0.1044, 0.0, 0.1829378, 0.0, 0.5116089, 222.35404, 0.8926889, 0.0042311, 0.55764, 0.6388089, 56.09232, 0.06204, 0.0010666500000000002, 0.94411555, 2.21745335, 2.2134310999999998, 0.07518665, 5.3895778, 107.9775822, 0.45789335, 6.630742199999999, 3.9506622, 0.0778711, 1.38529335, 2.4543600000000003, 0.0, 0.0, 2.0692444500000002, 296.4337511, 1.33, 0.00196445, 14.738719999999999, 0.60405335, 71.8430711, 0.5888, 0.2242578, 4.3458000000000006, 0.7147511, 1.6864889, 0.29070665, 1.77730665, 32.82137335, 8.38039555, 0.0002311, 1.5319689, 0.0729289, 12.64518665, 1.0240889, 1.6373777999999999, 0.0, 3.99210665, 11.497502200000001, 0.0, 2.3842222, 0.73431555, 2.1977289, 20.2637689, 2.2872178, 1.2342578000000002, 5.22692445, 16.71535555, 6.2038889, 0.00019555, 0.6802311, 89.23081334999999, 1.07349335, 6.27891555, 0.80864, 0.0037911, 0.4570222, 0.2981111, 0.9225111, 0.0, 0.0, 224.8047911, 2.1905111, 0.03306665, 0.9157822, 0.7166222, 56.9383378, 0.45935109999999996, 0.04504445, 1.78088, 3.61152, 1.9531111, 0.2379511, 7.4734489, 61.23908, 9.7350178, 62.49636, 11.35793335, 0.0961022, 11.91536, 3.2764666499999997, 8.9037289, 0.0, 3.61695555, 0.0, 14.046875550000001, 1.34168445, 3.04822665, 4.8021822, 61.57576445, 1.6124577999999998, 8.45828, 12.83554665, 12.4279378, 11.41213335, 1.83140445, 5.81970665, 84.4967022, 19.12669335, 0.0, 11.23270665, 0.0740889, 18.39219555, 3.6382889, 11.800715550000001, 0.0, 16.71745335, 42.80903555, 0.0, 1.6014088999999998, 3.4556889, 11.55799555, 51.1257378, 7.2742978, 19.855, 10.4886489, 23.37299555, 16.057826650000003, 0.27804445, 0.15495555, 3.9492178, 0.10140445, 1.7684222, 0.00688, 0.0, 0.17770665, 0.0062222, 0.049008899999999994, 0.0, 0.2549422, 17.6379911, 0.0396578, 0.0, 0.0007111, 0.00432445, 4.57036, 0.0015778, 0.0151689, 0.0169511, 0.15657335, 0.40577335, 0.007044450000000001, 0.14656444999999999, 0.6634622, 0.43748000000000004, 1.1684755500000001, 0.90123555, 0.0, 0.14247555, 0.23268445, 1.8909821999999998, 0.0, 0.24823555, 1.14628, 0.20724889999999999, 0.0002311, 0.0, 0.0, 0.44461335, 0.023551100000000002, 0.00707555, 0.0, 0.09778664999999999, 0.0, 0.00502665, 10.65121335, 3.15623555, 0.7604, 3.86984445, 4.3510622, 0.0181111, 0.8037911, 4.90504, 5.22426665, 0.0, 0.6337200000000001, 2.58195555, 0.5394711, 0.25372445, 0.0, 0.0, 8.171368900000001, 0.56812445, 2.0947911, 0.0, 0.65861335, 0.0, 0.0980222, 6.58978665, 77.12023555, 10.910084450000001, 57.32171555, 158.82272445, 0.11100445, 6.3600311000000005, 112.63644445, 170.28059555, 0.0, 89.08508445, 13.09176, 10.65531555, 28.696337800000002, 0.15460445, 4.59587555, 0.0, 0.6884089, 8.507635550000002, 1.3390178000000001, 14.4344222, 7.144399999999999, 0.4665822, 0.74447555, 25.7543911, 0.3678622, 1.6235822, 0.15002664999999998, 0.0, 0.08076445, 0.09738665, 0.1056978, 0.0, 0.39664445, 87.6466222, 0.3008978, 0.00156, 0.01367555, 0.5131955500000001, 21.1116089, 0.0, 0.37559555, 0.01617335, 0.60633335, 0.21400444999999998, 0.00705335, 0.3531511, 3.99557335, 1.91956, 14.7799111, 0.02382665, 0.41556445000000003, 3.9760578, 0.0013466499999999998, 0.3809289, 0.0, 0.61093335, 11.89710665, 0.7815866499999999, 0.0332311, 0.4058489, 5.0089822, 7.98881335, 0.0607778, 0.0, 1.3348622, 1.28221335, 0.12728, 0.058986649999999995, 0.14490665000000003, 5.6589778, 0.6072889, 10.3227511, 4.29665335, 0.00328, 1.2746711, 3.6997511, 1.8518711, 0.0, 0.8857466500000001, 7.54291555, 2.0470710999999997, 0.00707555, 0.0, 0.0044978, 6.466671099999999, 0.30794665, 0.3886978, 0.0, 0.9946755500000001, 0.0, 0.03181335, 1.5736978, 8.8743689, 2.30811555, 20.8394978, 0.39319555, 0.0164489, 2.49864, 0.038031100000000005, 0.44775555, 0.0, 0.5192711000000001, 14.9290578, 2.1236089000000002, 0.08823109999999999, 0.0599689, 0.48840445, 4.62548445, 1.4058711000000002, 0.42901335, 0.6390311000000001, 0.0, 0.9702578, 0.1006711, 0.42932889999999996, 1.44070665, 0.9271911, 15.36031555, 2.99211555, 0.01447555, 0.70419555, 1.04066665, 3.87343555, 0.0, 1.1775289, 5.726319999999999, 3.5881066500000003, 0.0577111, 0.0, 0.00021335, 3.7120755500000002, 0.20494665, 0.09831555, 0.0, 0.6068222, 0.0, 0.038377800000000004, 0.09272445, 0.033102200000000005, 0.53559555, 0.041008899999999994, 0.0001778, 0.0024044500000000003, 0.6562178, 0.13584000000000002, 0.50983555, 0.0, 0.68336445, 0.6162578, 0.24247555, 0.006542200000000001, 0.19656890000000002, 0.10434665, 1.3274311, 0.22333779999999998, 0.06179555, 1.08002665, 0.81050665, 0.27546665000000004, 0.0]
        def get_flow_list(m):
          return (str(m*lambda_time)+'M')
        flow_list = map(get_flow_list,flow_float)
        cli_outs = []
        ser_outs = []
#==========================modify start==================================
        _len = len(host_list)
        for i in xrange(1, _len):
            client = host_list[i]
            for j in xrange(1, _len):
                if client != host_list[j]:
                    server = host_list[j]
                    server_list.append(server)
                    bw = flow_list[(i-1)*23+j-1]
                    self.iperf_single(hosts = [client, server], udpBw=bw, period= period, port=base_port)
                    sleep(.30)
                    base_port += 1
        sleep(period)
        print "test has done"
#==========================modify end  ==================================
        # _len = len(host_list)
        # for i in xrange(0, _len):
        #     client = host_list[i]
        #     server = client
        #     while( server == client ):
        #         server = random.choice(host_list) 
        #     server_list.append(server)
        #     self.iperf_single(hosts = [client, server], udpBw=bw, period= period, port=base_port)
        #     sleep(.05)
        #     base_port += 1
 
        # sleep(period)
        # print "test has done"
#.....................................add...................................
    def waitConnected( self, timeout=None, delay=.5 ):
        """wait for each switch to connect to a controller,
           up to 5 seconds
           timeout: time to wait, or None to wait indefinitely
           delay: seconds to sleep per iteration
           returns: True if all switches are connected"""
        info( '*** Waiting for switches to connect\n' )
        time = 0
        remaining = list( self.switches )
        while True:
            for switch in tuple( remaining ):
                if switch.connected():
                    info( '%s ' % switch )
                    remaining.remove( switch )
            if not remaining:
                info( '\n' )
                return True
            if time > timeout and timeout is not None:
                break
            sleep( delay )
            time += delay
        warn( 'Timed out after %d seconds\n' % time )
        for switch in remaining:
            if not switch.connected():
                warn( 'Warning: %s is not connected to a controller\n'
                      % switch.name )
            else:
                remaining.remove( switch )
        return not remaining

    def addHost( self, name, cls=None, **params ):
        """Add host.
           name: name of host to add
           cls: custom host class/constructor (optional)
           params: parameters for host
           returns: added host"""
        # Default IP and MAC addresses
        defaults = { 'ip': ipAdd( self.nextIP,
                                  ipBaseNum=self.ipBaseNum,
                                  prefixLen=self.prefixLen ) +
                                  '/%s' % self.prefixLen }
        if self.autoSetMacs:
            defaults[ 'mac' ] = macColonHex( self.nextIP )
        if self.autoPinCpus:
            defaults[ 'cores' ] = self.nextCore
            self.nextCore = ( self.nextCore + 1 ) % self.numCores
        self.nextIP += 1
        defaults.update( params )
        if not cls:
            cls = self.host
        h = cls( name, **defaults )
        self.hosts.append( h )
        self.nameToNode[ name ] = h
        return h

    def delNode( self, node, nodes=None):
        """Delete node
           node: node to delete
           nodes: optional list to delete from (e.g. self.hosts)"""
        if nodes is None:
            nodes = ( self.hosts if node in self.hosts else
                      ( self.switches if node in self.switches else
                        ( self.controllers if node in self.controllers else
                          [] ) ) )
        node.stop( deleteIntfs=True )
        node.terminate()
        nodes.remove( node )
        del self.nameToNode[ node.name ]

    def delHost( self, host ):
        "Delete a host"
        self.delNode( host, nodes=self.hosts )

    def addSwitch( self, name, cls=None, **params ):
        """Add switch.
           name: name of switch to add
           cls: custom switch class/constructor (optional)
           returns: added switch
           side effect: increments listenPort ivar ."""
        defaults = { 'listenPort': self.listenPort,
                     'inNamespace': self.inNamespace }
        defaults.update( params )
        if not cls:
            cls = self.switch
        sw = cls( name, **defaults )
        if not self.inNamespace and self.listenPort:
            self.listenPort += 1
        self.switches.append( sw )
        self.nameToNode[ name ] = sw
        return sw

    def delSwitch( self, switch ):
        "Delete a switch"
        self.delNode( switch, nodes=self.switches )

    def addController( self, name='c0', controller=None, **params ):
        """Add controller.
           controller: Controller class"""
        # Get controller class
        if not controller:
            controller = self.controller
        # Construct new controller if one is not given
        if isinstance( name, Controller ):
            controller_new = name
            # Pylint thinks controller is a str()
            # pylint: disable=maybe-no-member
            name = controller_new.name
            # pylint: enable=maybe-no-member
        else:
            controller_new = controller( name, **params )
        # Add new controller to net
        if controller_new:  # allow controller-less setups
            self.controllers.append( controller_new )
            self.nameToNode[ name ] = controller_new
        return controller_new

    def delController( self, controller ):
        """Delete a controller
           Warning - does not reconfigure switches, so they
           may still attempt to connect to it!"""
        self.delNode( controller )

    def addNAT( self, name='nat0', connect=True, inNamespace=False,
                **params):
        """Add a NAT to the Mininet network
           name: name of NAT node
           connect: switch to connect to | True (s1) | None
           inNamespace: create in a network namespace
           params: other NAT node params, notably:
               ip: used as default gateway address"""
        nat = self.addHost( name, cls=NAT, inNamespace=inNamespace,
                            subnet=self.ipBase, **params )
        # find first switch and create link
        if connect:
            if not isinstance( connect, Node ):
                # Use first switch if not specified
                connect = self.switches[ 0 ]
            # Connect the nat to the switch
            self.addLink( nat, connect )
            # Set the default route on hosts
            natIP = nat.params[ 'ip' ].split('/')[ 0 ]
            for host in self.hosts:
                if host.inNamespace:
                    host.setDefaultRoute( 'via %s' % natIP )
        return nat

    # BL: We now have four ways to look up nodes
    # This may (should?) be cleaned up in the future.
    def getNodeByName( self, *args ):
        "Return node(s) with given name(s)"
        if len( args ) == 1:
            return self.nameToNode[ args[ 0 ] ]
        return [ self.nameToNode[ n ] for n in args ]

    def get( self, *args ):
        "Convenience alias for getNodeByName"
        return self.getNodeByName( *args )

    # Even more convenient syntax for node lookup and iteration
    def __getitem__( self, key ):
        "net[ name ] operator: Return node with given name"
        return self.nameToNode[ key ]

    def __delitem__( self, key ):
        "del net[ name ] operator - delete node with given name"
        self.delNode( self.nameToNode[ key ] )

    def __iter__( self ):
        "return iterator over node names"
        for node in chain( self.hosts, self.switches, self.controllers ):
            yield node.name

    def __len__( self ):
        "returns number of nodes in net"
        return ( len( self.hosts ) + len( self.switches ) +
                 len( self.controllers ) )

    def __contains__( self, item ):
        "returns True if net contains named node"
        return item in self.nameToNode

    def keys( self ):
        "return a list of all node names or net's keys"
        return list( self )

    def values( self ):
        "return a list of all nodes or net's values"
        return [ self[name] for name in self ]

    def items( self ):
        "return (key,value) tuple list for every node in net"
        return zip( self.keys(), self.values() )

    @staticmethod
    def randMac():
        "Return a random, non-multicast MAC address"
        return macColonHex( random.randint(1, 2**48 - 1) & 0xfeffffffffff |
                            0x020000000000 )

    def addLink( self, node1, node2, port1=None, port2=None,
                 cls=None, **params ):
        """"Add a link from node1 to node2
            node1: source node (or name)
            node2: dest node (or name)
            port1: source port (optional)
            port2: dest port (optional)
            cls: link class (optional)
            params: additional link params (optional)
            returns: link object"""
        # Accept node objects or names
        node1 = node1 if not isinstance( node1, basestring ) else self[ node1 ]
        node2 = node2 if not isinstance( node2, basestring ) else self[ node2 ]
        options = dict( params )
        # Port is optional
        if port1 is not None:
            options.setdefault( 'port1', port1 )
        if port2 is not None:
            options.setdefault( 'port2', port2 )
        if self.intf is not None:
            options.setdefault( 'intf', self.intf )
        # Set default MAC - this should probably be in Link
        options.setdefault( 'addr1', self.randMac() )
        options.setdefault( 'addr2', self.randMac() )
        cls = self.link if cls is None else cls
        link = cls( node1, node2, **options )
        self.links.append( link )
        return link

    def delLink( self, link ):
        "Remove a link from this network"
        link.delete()
        self.links.remove( link )

    def linksBetween( self, node1, node2 ):
        "Return Links between node1 and node2"
        return [ link for link in self.links
                 if ( node1, node2 ) in (
                    ( link.intf1.node, link.intf2.node ),
                    ( link.intf2.node, link.intf1.node ) ) ]

    def delLinkBetween( self, node1, node2, index=0, allLinks=False ):
        """Delete link(s) between node1 and node2
           index: index of link to delete if multiple links (0)
           allLinks: ignore index and delete all such links (False)
           returns: deleted link(s)"""
        links = self.linksBetween( node1, node2 )
        if not allLinks:
            links = [ links[ index ] ]
        for link in links:
            self.delLink( link )
        return links

    def configHosts( self ):
        "Configure a set of hosts."
        for host in self.hosts:
            info( host.name + ' ' )
            intf = host.defaultIntf()
            if intf:
                host.configDefault()
            else:
                # Don't configure nonexistent intf
                host.configDefault( ip=None, mac=None )
            # You're low priority, dude!
            # BL: do we want to do this here or not?
            # May not make sense if we have CPU lmiting...
            # quietRun( 'renice +18 -p ' + repr( host.pid ) )
            # This may not be the right place to do this, but
            # it needs to be done somewhere.
        info( '\n' )

    def buildFromTopo( self, topo=None ):
        """Build mininet from a topology object
           At the end of this function, everything should be connected
           and up."""

        # Possibly we should clean up here and/or validate
        # the topo
        if self.cleanup:
            pass

        info( '*** Creating network\n' )

        if not self.controllers and self.controller:
            # Add a default controller
            info( '*** Adding controller\n' )
            classes = self.controller
            if not isinstance( classes, list ):
                classes = [ classes ]
            for i, cls in enumerate( classes ):
                # Allow Controller objects because nobody understands partial()
                if isinstance( cls, Controller ):
                    self.addController( cls )
                else:
                    self.addController( 'c%d' % i, cls )

        info( '*** Adding hosts:\n' )
        for hostName in topo.hosts():
            self.addHost( hostName, **topo.nodeInfo( hostName ) )
            info( hostName + ' ' )

        info( '\n*** Adding switches:\n' )
        for switchName in topo.switches():
            # A bit ugly: add batch parameter if appropriate
            params = topo.nodeInfo( switchName)
            cls = params.get( 'cls', self.switch )
            if hasattr( cls, 'batchStartup' ):
                params.setdefault( 'batch', True )
            self.addSwitch( switchName, **params )
            info( switchName + ' ' )

        info( '\n*** Adding links:\n' )
        for srcName, dstName, params in topo.links(
                sort=True, withInfo=True ):
            self.addLink( **params )
            info( '(%s, %s) ' % ( srcName, dstName ) )

        info( '\n' )

    def configureControlNetwork( self ):
        "Control net config hook: override in subclass"
        raise Exception( 'configureControlNetwork: '
                         'should be overriden in subclass', self )

    def build( self ):
        "Build mininet."
        if self.topo:
            self.buildFromTopo( self.topo )
        if self.inNamespace:
            self.configureControlNetwork()
        info( '*** Configuring hosts\n' )
        self.configHosts()
        if self.xterms:
            self.startTerms()
        if self.autoStaticArp:
            self.staticArp()
        self.built = True

    def startTerms( self ):
        "Start a terminal for each node."
        if 'DISPLAY' not in os.environ:
            error( "Error starting terms: Cannot connect to display\n" )
            return
        info( "*** Running terms on %s\n" % os.environ[ 'DISPLAY' ] )
        cleanUpScreens()
        self.terms += makeTerms( self.controllers, 'controller' )
        self.terms += makeTerms( self.switches, 'switch' )
        self.terms += makeTerms( self.hosts, 'host' )

    def stopXterms( self ):
        "Kill each xterm."
        for term in self.terms:
            os.kill( term.pid, signal.SIGKILL )
        cleanUpScreens()

    def staticArp( self ):
        "Add all-pairs ARP entries to remove the need to handle broadcast."
        for src in self.hosts:
            for dst in self.hosts:
                if src != dst:
                    src.setARP( ip=dst.IP(), mac=dst.MAC() )

    def start( self ):
        "Start controller and switches."
        if not self.built:
            self.build()
        info( '*** Starting controller\n' )
        for controller in self.controllers:
            info( controller.name + ' ')
            controller.start()
        info( '\n' )
        info( '*** Starting %s switches\n' % len( self.switches ) )
        for switch in self.switches:
            info( switch.name + ' ')
            switch.start( self.controllers )
        started = {}
        for swclass, switches in groupby(
                sorted( self.switches, key=type ), type ):
            switches = tuple( switches )
            if hasattr( swclass, 'batchStartup' ):
                success = swclass.batchStartup( switches )
                started.update( { s: s for s in success } )
        info( '\n' )
        if self.waitConn:
            self.waitConnected()

    def stop( self ):
        "Stop the controller(s), switches and hosts"
        info( '*** Stopping %i controllers\n' % len( self.controllers ) )
        for controller in self.controllers:
            info( controller.name + ' ' )
            controller.stop()
        info( '\n' )
        if self.terms:
            info( '*** Stopping %i terms\n' % len( self.terms ) )
            self.stopXterms()
        info( '*** Stopping %i links\n' % len( self.links ) )
        for link in self.links:
            info( '.' )
            link.stop()
        info( '\n' )
        info( '*** Stopping %i switches\n' % len( self.switches ) )
        stopped = {}
        for swclass, switches in groupby(
                sorted( self.switches, key=type ), type ):
            switches = tuple( switches )
            if hasattr( swclass, 'batchShutdown' ):
                success = swclass.batchShutdown( switches )
                stopped.update( { s: s for s in success } )
        for switch in self.switches:
            info( switch.name + ' ' )
            if switch not in stopped:
                switch.stop()
            switch.terminate()
        info( '\n' )
        info( '*** Stopping %i hosts\n' % len( self.hosts ) )
        for host in self.hosts:
            info( host.name + ' ' )
            host.terminate()
        info( '\n*** Done\n' )

    def run( self, test, *args, **kwargs ):
        "Perform a complete start/test/stop cycle."
        self.start()
        info( '*** Running test\n' )
        result = test( *args, **kwargs )
        self.stop()
        return result

    def monitor( self, hosts=None, timeoutms=-1 ):
        """Monitor a set of hosts (or all hosts by default),
           and return their output, a line at a time.
           hosts: (optional) set of hosts to monitor
           timeoutms: (optional) timeout value in ms
           returns: iterator which returns host, line"""
        if hosts is None:
            hosts = self.hosts
        poller = select.poll()
        h1 = hosts[ 0 ]  # so we can call class method fdToNode
        for host in hosts:
            poller.register( host.stdout )
        while True:
            ready = poller.poll( timeoutms )
            for fd, event in ready:
                host = h1.fdToNode( fd )
                if event & select.POLLIN:
                    line = host.readline()
                    if line is not None:
                        yield host, line
            # Return if non-blocking
            if not ready and timeoutms >= 0:
                yield None, None

    # XXX These test methods should be moved out of this class.
    # Probably we should create a tests.py for them

    @staticmethod
    def _parsePing( pingOutput ):
        "Parse ping output and return packets sent, received."
        # Check for downed link
        if 'connect: Network is unreachable' in pingOutput:
            return 1, 0
        r = r'(\d+) packets transmitted, (\d+)( packets)? received'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return 1, 0
        sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
        return sent, received

    def ping( self, hosts=None, timeout=None ):
        """Ping between all specified hosts.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: ploss packet loss percentage"""
        # should we check if running?
        packets = 0
        lost = 0
        ploss = None
        if not hosts:
            hosts = self.hosts
            output( '*** Ping: testing ping reachability\n' )
        for node in hosts:
            output( '%s -> ' % node.name )
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    if dest.intfs:
                        result = node.cmd( 'ping -c1 %s %s' %
                                           (opts, dest.IP()) )
                        sent, received = self._parsePing( result )
                    else:
                        sent, received = 0, 0
                    packets += sent
                    if received > sent:
                        error( '*** Error: received too many packets' )
                        error( '%s' % result )
                        node.cmdPrint( 'route' )
                        exit( 1 )
                    lost += sent - received
                    output( ( '%s ' % dest.name ) if received else 'X ' )
            output( '\n' )
        if packets > 0:
            ploss = 100.0 * lost / packets
            received = packets - lost
            output( "*** Results: %i%% dropped (%d/%d received)\n" %
                    ( ploss, received, packets ) )
        else:
            ploss = 0
            output( "*** Warning: No packets sent\n" )
        return ploss

    @staticmethod
    def _parsePingFull( pingOutput ):
        "Parse ping output and return all data."
        errorTuple = (1, 0, 0, 0, 0, 0)
        # Check for downed link
        r = r'[uU]nreachable'
        m = re.search( r, pingOutput )
        if m is not None:
            return errorTuple
        r = r'(\d+) packets transmitted, (\d+)( packets)? received'
        m = re.search( r, pingOutput )
        if m is None:
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return errorTuple
        sent, received = int( m.group( 1 ) ), int( m.group( 2 ) )
        r = r'rtt min/avg/max/mdev = '
        r += r'(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+) ms'
        m = re.search( r, pingOutput )
        if m is None:
            if received == 0:
                return errorTuple
            error( '*** Error: could not parse ping output: %s\n' %
                   pingOutput )
            return errorTuple
        rttmin = float( m.group( 1 ) )
        rttavg = float( m.group( 2 ) )
        rttmax = float( m.group( 3 ) )
        rttdev = float( m.group( 4 ) )
        return sent, received, rttmin, rttavg, rttmax, rttdev

    def pingFull( self, hosts=None, timeout=None ):
        """Ping between all specified hosts and return all data.
           hosts: list of hosts
           timeout: time to wait for a response, as string
           returns: all ping data; see function body."""
        # should we check if running?
        # Each value is a tuple: (src, dsd, [all ping outputs])
        all_outputs = []
        if not hosts:
            hosts = self.hosts
            output( '*** Ping: testing ping reachability\n' )
        for node in hosts:
            output( '%s -> ' % node.name )
            for dest in hosts:
                if node != dest:
                    opts = ''
                    if timeout:
                        opts = '-W %s' % timeout
                    result = node.cmd( 'ping -c1 %s %s' % (opts, dest.IP()) )
                    outputs = self._parsePingFull( result )
                    sent, received, rttmin, rttavg, rttmax, rttdev = outputs
                    all_outputs.append( (node, dest, outputs) )
                    output( ( '%s ' % dest.name ) if received else 'X ' )
            output( '\n' )
        output( "*** Results: \n" )
        for outputs in all_outputs:
            src, dest, ping_outputs = outputs
            sent, received, rttmin, rttavg, rttmax, rttdev = ping_outputs
            output( " %s->%s: %s/%s, " % (src, dest, sent, received ) )
            output( "rtt min/avg/max/mdev %0.3f/%0.3f/%0.3f/%0.3f ms\n" %
                    (rttmin, rttavg, rttmax, rttdev) )
        return all_outputs

    def pingAll( self, timeout=None ):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        return self.ping( timeout=timeout )

    def pingPair( self ):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        hosts = [ self.hosts[ 0 ], self.hosts[ 1 ] ]
        return self.ping( hosts=hosts )

    def pingAllFull( self ):
        """Ping between all hosts.
           returns: ploss packet loss percentage"""
        return self.pingFull()

    def pingPairFull( self ):
        """Ping between first two hosts, useful for testing.
           returns: ploss packet loss percentage"""
        hosts = [ self.hosts[ 0 ], self.hosts[ 1 ] ]
        return self.pingFull( hosts=hosts )

    @staticmethod
    def _parseIperf( iperfOutput ):
        """Parse iperf output and return bandwidth.
           iperfOutput: string
           returns: result string"""
        r = r'([\d\.]+ \w+/sec)'
        m = re.findall( r, iperfOutput )
        if m:
            return m[-1]
        else:
            # was: raise Exception(...)
            error( 'could not parse iperf output: ' + iperfOutput )
            return ''

    # XXX This should be cleaned up

    def iperf( self, hosts=None, l4Type='TCP', udpBw='10M', fmt=None,
               seconds=5, port=5001):
        """Run iperf between two hosts.
           hosts: list of hosts; if None, uses first and last hosts
           l4Type: string, one of [ TCP, UDP ]
           udpBw: bandwidth target for UDP test
           fmt: iperf format argument if any
           seconds: iperf time to transmit
           port: iperf port
           returns: two-element array of [ server, client ] speeds
           note: send() is buffered, so client rate can be much higher than
           the actual transmission rate; on an unloaded system, server
           rate should be much closer to the actual receive rate"""
        hosts = hosts or [ self.hosts[ 0 ], self.hosts[ -1 ] ]
        assert len( hosts ) == 2
        client, server = hosts
        output( '*** Iperf: testing', l4Type, 'bandwidth between',
                client, 'and', server, '\n' )
        server.cmd( 'killall -9 iperf' )
        iperfArgs = 'iperf -p %d ' % port
        bwArgs = ''
        if l4Type == 'UDP':
            iperfArgs += '-u '
            bwArgs = '-b ' + udpBw + ' '
        elif l4Type != 'TCP':
            raise Exception( 'Unexpected l4 type: %s' % l4Type )
        if fmt:
            iperfArgs += '-f %s ' % fmt
        server.sendCmd( iperfArgs + '-s' )
        if l4Type == 'TCP':
            if not waitListening( client, server.IP(), port ):
                raise Exception( 'Could not connect to iperf on port %d'
                                 % port )
        cliout = client.cmd( iperfArgs + '-t %d -c ' % seconds +
                             server.IP() + ' ' + bwArgs )
        debug( 'Client output: %s\n' % cliout )
        servout = ''
        # We want the last *b/sec from the iperf server output
        # for TCP, there are two of them because of waitListening
        count = 2 if l4Type == 'TCP' else 1
        while len( re.findall( '/sec', servout ) ) < count:
            servout += server.monitor( timeoutms=5000 )
        server.sendInt()
        servout += server.waitOutput()
        debug( 'Server output: %s\n' % servout )
        result = [ self._parseIperf( servout ), self._parseIperf( cliout ) ]
        if l4Type == 'UDP':
            result.insert( 0, udpBw )
        output( '*** Results: %s\n' % result )
        return result

    def runCpuLimitTest( self, cpu, duration=5 ):
        """run CPU limit test with 'while true' processes.
        cpu: desired CPU fraction of each host
        duration: test duration in seconds (integer)
        returns a single list of measured CPU fractions as floats.
        """
        pct = cpu * 100
        info( '*** Testing CPU %.0f%% bandwidth limit\n' % pct )
        hosts = self.hosts
        cores = int( quietRun( 'nproc' ) )
        # number of processes to run a while loop on per host
        num_procs = int( ceil( cores * cpu ) )
        pids = {}
        for h in hosts:
            pids[ h ] = []
            for _core in range( num_procs ):
                h.cmd( 'while true; do a=1; done &' )
                pids[ h ].append( h.cmd( 'echo $!' ).strip() )
        outputs = {}
        time = {}
        # get the initial cpu time for each host
        for host in hosts:
            outputs[ host ] = []
            with open( '/sys/fs/cgroup/cpuacct/%s/cpuacct.usage' %
                       host, 'r' ) as f:
                time[ host ] = float( f.read() )
        for _ in range( duration ):
            sleep( 1 )
            for host in hosts:
                with open( '/sys/fs/cgroup/cpuacct/%s/cpuacct.usage' %
                           host, 'r' ) as f:
                    readTime = float( f.read() )
                outputs[ host ].append( ( ( readTime - time[ host ] )
                                        / 1000000000 ) / cores * 100 )
                time[ host ] = readTime
        for h, pids in pids.items():
            for pid in pids:
                h.cmd( 'kill -9 %s' % pid )
        cpu_fractions = []
        for _host, outputs in outputs.items():
            for pct in outputs:
                cpu_fractions.append( pct )
        output( '*** Results: %s\n' % cpu_fractions )
        return cpu_fractions

    # BL: I think this can be rewritten now that we have
    # a real link class.
    def configLinkStatus( self, src, dst, status ):
        """Change status of src <-> dst links.
           src: node name
           dst: node name
           status: string {up, down}"""
        if src not in self.nameToNode:
            error( 'src not in network: %s\n' % src )
        elif dst not in self.nameToNode:
            error( 'dst not in network: %s\n' % dst )
        else:
            src = self.nameToNode[ src ]
            dst = self.nameToNode[ dst ]
            connections = src.connectionsTo( dst )
            if len( connections ) == 0:
                error( 'src and dst not connected: %s %s\n' % ( src, dst) )
            for srcIntf, dstIntf in connections:
                result = srcIntf.ifconfig( status )
                if result:
                    error( 'link src status change failed: %s\n' % result )
                result = dstIntf.ifconfig( status )
                if result:
                    error( 'link dst status change failed: %s\n' % result )

    def interact( self ):
        "Start network and run our simple CLI."
        self.start()
        result = CLI( self )
        self.stop()
        return result

    inited = False

    @classmethod
    def init( cls ):
        "Initialize Mininet"
        if cls.inited:
            return
        ensureRoot()
        fixLimits()
        cls.inited = True


class MininetWithControlNet( Mininet ):

    """Control network support:

       Create an explicit control network. Currently this is only
       used/usable with the user datapath.

       Notes:

       1. If the controller and switches are in the same (e.g. root)
          namespace, they can just use the loopback connection.

       2. If we can get unix domain sockets to work, we can use them
          instead of an explicit control network.

       3. Instead of routing, we could bridge or use 'in-band' control.

       4. Even if we dispense with this in general, it could still be
          useful for people who wish to simulate a separate control
          network (since real networks may need one!)

       5. Basically nobody ever used this code, so it has been moved
          into its own class.

       6. Ultimately we may wish to extend this to allow us to create a
          control network which every node's control interface is
          attached to."""

    def configureControlNetwork( self ):
        "Configure control network."
        self.configureRoutedControlNetwork()

    # We still need to figure out the right way to pass
    # in the control network location.

    def configureRoutedControlNetwork( self, ip='192.168.123.1',
                                       prefixLen=16 ):
        """Configure a routed control network on controller and switches.
           For use with the user datapath only right now."""
        controller = self.controllers[ 0 ]
        info( controller.name + ' <->' )
        cip = ip
        snum = ipParse( ip )
        for switch in self.switches:
            info( ' ' + switch.name )
            link = self.link( switch, controller, port1=0 )
            sintf, cintf = link.intf1, link.intf2
            switch.controlIntf = sintf
            snum += 1
            while snum & 0xff in [ 0, 255 ]:
                snum += 1
            sip = ipStr( snum )
            cintf.setIP( cip, prefixLen )
            sintf.setIP( sip, prefixLen )
            controller.setHostRoute( sip, cintf )
            switch.setHostRoute( cip, sintf )
        info( '\n' )
        info( '*** Testing control network\n' )
        while not cintf.isUp():
            info( '*** Waiting for', cintf, 'to come up\n' )
            sleep( 1 )
        for switch in self.switches:
            while not sintf.isUp():
                info( '*** Waiting for', sintf, 'to come up\n' )
                sleep( 1 )
            if self.ping( hosts=[ switch, controller ] ) != 0:
                error( '*** Error: control network test failed\n' )
                exit( 1 )
        info( '\n' )
