#!/usr/bin/env python
#-*- coding: utf-8 -*-


from pox.lib.revent.revent import EventMixin, Event
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.vlan import vlan
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4
from pox.lib.packet.ethernet import ethernet
from pox.lib.recoco import Timer
import pox.lib.util as util
from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt

import time

log = core.getLogger()


class NewMonitor(Event):
    """
    NewMonitor事件，包括host的各种信息
    """
    def __init__(self, **kw):
        Event.__init__(self)
        #we need the information to locate the monitor host.
        self.hw = kw.get('hw')
        self.ip = kw.get('ip')
        self.dpid = kw.get('dpid')
        self.switch_port = kw.get('switch_port')
        self.match = kw.get('match')

    def __repr__(self):
        return self

class Handle_PacketIn(EventMixin):
    _core_name = "opennetmon_handle_PacketIn"
    #要raise NewMonitor事件，_eventMixin_events加入NewMonitor类
    _eventMixin_events = set([
                            NewMonitor,
                            ])

    def __init__(self):
        log.debug("Handle_PacketIn coming up.")
        # addListeners监听PacketIn事件
        core.openflow.addListeners(self)
        log.debug("handle_PacketIn startup.")

    def _handle_PacketIn(self, event):
       
       #通知ovs丢弃数据包
        def drop():
            """Tell the switch to drop the packet"""
            if event.ofp.buffer_id is not None: #nothing to drop because the packet is not in the Switch buffer
                msg = of.ofp_packet_out()
                msg.buffer_id = event.ofp.buffer_id 
                event.ofp.buffer_id = None # Mark as dead, copied from James McCauley, not sure what it does but it does not work otherwise
                msg.in_port = event.port
                event.connection.send(msg)
        #响应请求10.0.0.2的ARP request
        def arp_response(a):
            r = arp()
            r.hwtype = a.hwtype
            r.prototype = a.prototype
            r.hwlen = a.hwlen
            r.protolen = a.protolen
            r.opcode = arp.REPLY
            r.hwdst = a.hwsrc
            r.protodst = a.protosrc
            r.protosrc = a.protodst
            r.hwsrc = EthAddr('00:00:00:00:00:02')
            e = ethernet(type=packet.type, src=EthAddr('00:00:00:00:00:02'),
                        dst=a.hwsrc)
            e.payload = r
            if packet.type == ethernet.VLAN_TYPE:
                v_rcv = packet.find('vlan')
                e.payload = vlan(eth_type = e.type,
                                 payload = e.payload,
                                 id = v_rcv.id,
                                 pcp = v_rcv.pcp)
                e.type = ethernet.VLAN_TYPE
            msg = of.ofp_packet_out()
            msg.data = e.pack()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
            msg.in_port = event.port
            event.connection.send(msg)

        #解析event
        packet = event.parsed

        #如果是要请求10.0.0.2的ARP request，响应它
        if packet.find('arp'):
            a = packet.find('arp')
            if a:
                if a.prototype == arp.PROTO_TYPE_IP:
                    if a.hwtype == arp.HW_TYPE_ETHERNET:
                        if a.protosrc != 0:
                            if a.opcode == arp.REQUEST:
                                # Maybe we can answer
                                if a.protodst == IPAddr('10.0.0.2'):
                                    log.debug("find arp REQUEST")
                                    arp_response(a)
        #探测到10.0.0.1的udp报文raiseEvent NewMonitor事件，通知Monitoring下发流表
        elif packet.find('ipv4') and packet.find('udp') and not packet.find('icmp'):
            # log.debug("switch %s port %s find udp packet.", util.dpid_to_str(event.connection.dpid), event.port)
            ip_packet = packet.find('ipv4')
            if ip_packet.srcip == IPAddr('10.0.0.1') and ip_packet.dstip == IPAddr('10.0.0.2'):
                match = of.ofp_match.from_packet(packet)
                match.dl_src, match.dl_dst = (None, None)
                self.raiseEvent(NewMonitor(match = match, ip = ip_packet.srcip, hw = packet.src, dpid = event.dpid, switch_port = event.port))
                log.debug("monitor find at switch %s", util.dpid_to_str(event.connection.dpid))
        else:
            # drop()
            pass

def launch ():
    #注册Handle_PacketIn组件
    core.registerNew(Handle_PacketIn)
