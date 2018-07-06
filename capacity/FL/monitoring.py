#!/bin/bash/env python
#-*- coding: utf-8 -*-

"""
Listen NewMonitor evnent，install monitor flow table
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
import pox.lib.util as util
from pox.lib.recoco import Timer
from datetime import datetime
from collections import defaultdict
from collections import namedtuple
import pox.lib.packet as pkt
#from pox.openflow.of_json import flow_stats_to_list
import struct
from pox.lib.addresses import IPAddr,EthAddr
import time

log = core.getLogger()
switches = {}
switch_ports = {}
adj = defaultdict(lambda:defaultdict(lambda:None))

def _install_monitoring_path(monitor, monitors, paths, links, adj_path):
    switches_ip, path_id, switches_mac = {}, {}, {}

    class Path_id():
        """
        随机为每一个path分配一个固定udp端口号
        """
        def __init__(self):
            self.id_dict = {}
            # 去除9999
            self.id_list = (9999,)

        def __getitem__(self, path):
            if path in self.id_dict.keys():
                return self.id_dict[path]
            x = path
            if not isinstance(path, tuple):
                x = tuple(path)
            i = hash(x)%(1<<15)
            while i in self.id_list:
                i = (i + 1)%(1<<15)
            self.id_list = self.id_list + (i,)
            self.id_dict[path] = i
            return i

        def keys(self):
            return self.id_dict.keys()
            
    path_id = Path_id()
    def topo_conf():
        """
        Each switch is configed with a ip address. You can config it with files yourself .
        """
        for k in switches.keys():
            switches_ip[k] = IPAddr((192<<24)+int(k))
            switches_mac[k] = EthAddr("aa"+ "%010d"%(k))

    def install_SDN_path():
        
        #r24收到h1的probe后
        msg = of.ofp_flow_mod()
        msg.match = monitor.match.clone()  
        #匹配h1
        msg.match.tp_dst, msg.match.tp_src = (None,) * 2
        msg.match.nw_src = IPAddr('10.0.0.1')
        msg.match.nw_dst = IPAddr('10.0.0.2')
        msg.match.in_port = monitor.switch_port
        #转发
        for l1node in adj_path.keys():
            msg.actions.append(of.ofp_action_output(port=adj[monitor.dpid][l1node]))
        switches[monitor.dpid].connection.send(msg)

        #l1收到r24的probe后
        for l1node in adj_path.keys():
            msg = of.ofp_flow_mod(match=monitor.match.clone())
            #匹配
            msg.match.tp_dst, msg.match.tp_src = (None,) * 2
            msg.match.nw_src = IPAddr('10.0.0.1')
            msg.match.nw_dst = IPAddr('10.0.0.2')
            msg.match.in_port = adj[l1node][monitor.dpid]
            #modify ip and 向下转发
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr = switches_ip[l1node]))
            for l2node in adj_path[l1node].keys():
                msg.actions.append(of.ofp_action_output(port=adj[l1node][l2node]))
            #修改udp_port,发送回r24
            temp_path = []
            temp_path.append(24)
            temp_path.append(l1node)
            temp_path = tuple(temp_path)
            msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
            msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
            switches[l1node].connection.send(msg)

        #l2节点收到l1的probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                msg = of.ofp_flow_mod(match=monitor.match.clone())
                # 匹配
                msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                msg.match.nw_src = switches_ip[l1node]
                msg.match.nw_dst = IPAddr('10.0.0.2')
                msg.match.in_port = adj[l2node][l1node]
                # 向下转发
                for l3node in adj_path[l1node][l2node].keys():
                    msg.actions.append(of.ofp_action_output(port=adj[l2node][l3node]))
                #modify and send back
                temp_path = []
                temp_path.append(24)
                temp_path.append(l1node)
                temp_path.append(l2node)
                temp_path = tuple(temp_path)
                msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
                msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                switches[l2node].connection.send(msg)

        #l3节点收到l2probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                for l3node in adj_path[l1node][l2node].keys():
                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    # 匹配
                    msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                    msg.match.nw_src = switches_ip[l1node]
                    msg.match.nw_dst = IPAddr('10.0.0.2')
                    msg.match.in_port = adj[l3node][l2node]
                    # 向下转发
                    for l4node in adj_path[l1node][l2node][l3node].keys():
                        msg.actions.append(of.ofp_action_output(port=adj[l3node][l4node]))
                    #转发回去
                    temp_path = []
                    temp_path.append(24)
                    temp_path.append(l1node)
                    temp_path.append(l2node)
                    temp_path.append(l3node)
                    temp_path = tuple(temp_path)
                    msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
                    msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                    switches[l3node].connection.send(msg)

        #l4节点收到l3probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                for l3node in adj_path[l1node][l2node].keys():
                    for l4node in adj_path[l1node][l2node][l3node].keys():
                        msg = of.ofp_flow_mod(match=monitor.match.clone())
                        # 匹配
                        msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                        msg.match.nw_src = switches_ip[l1node]
                        msg.match.nw_dst = IPAddr('10.0.0.2')
                        msg.match.in_port = adj[l4node][l3node]

                        #modify and send back
                        temp_path = [24];
                        temp_path.append(l1node);temp_path.append(l2node)
                        temp_path.append(l3node);temp_path.append(l4node)
                        temp_path = tuple(temp_path)
                        msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
                        msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                        switches[l4node].connection.send(msg)

        #l3收到l4的probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                for l3node in adj_path[l1node][l2node].keys():
                    for l4node in adj_path[l1node][l2node][l3node].keys():
                        msg = of.ofp_flow_mod(match=monitor.match.clone())
                        # 匹配
                        msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                        msg.match.nw_src = switches_ip[l1node]
                        msg.match.nw_dst = IPAddr('10.0.0.2')
                        msg.match.in_port = adj[l3node][l4node]
                        #往上转发
                        msg.actions.append(of.ofp_action_output(port=adj[l3node][l2node]))
                        switches[l3node].connection.send(msg)
        #l2节点收到l3的probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                for l3node in adj_path[l1node][l2node].keys():
                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    # 匹配
                    msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                    msg.match.nw_src = switches_ip[l1node]
                    msg.match.nw_dst = IPAddr('10.0.0.2')
                    msg.match.in_port = adj[l2node][l3node]
                    #往上转发
                    msg.actions.append(of.ofp_action_output(port=adj[l2node][l1node]))
                    switches[l2node].connection.send(msg)

        #l1节点收到l2的probe以后
        for l1node in adj_path.keys():
            for l2node in adj_path[l1node].keys():
                msg = of.ofp_flow_mod(match=monitor.match.clone())
                msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                msg.match.nw_src = switches_ip[l1node]
                msg.match.nw_dst = IPAddr('10.0.0.2')
                msg.match.in_port = adj[l1node][l2node]
                #往上转发
                msg.actions.append(of.ofp_action_output(port=adj[l1node][monitor.dpid]))
                switches[l1node].connection.send(msg)

                log.debug('monitor num')

        #r24收到l1的probe以后
        for l1node in adj_path.keys():
            msg = of.ofp_flow_mod()
            msg.match = monitor.match.clone()   
            
            #匹配
            msg.match.nw_src, msg.match.tp_dst, msg.match.tp_src = (None,) * 3
            msg.match.nw_dst = IPAddr('10.0.0.2')
            msg.match.in_port = adj[monitor.dpid][l1node]

            #修改IP
            msg.actions.append(of.ofp_action_nw_addr.set_dst(nw_addr = monitor.ip))
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr = IPAddr('10.0.0.2')))
            msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = monitor.hw))
            msg.actions.append(of.ofp_action_dl_addr.set_src(dl_addr = EthAddr("00:00:00:00:00:02")))
            msg.actions.append(of.ofp_action_output(port=monitor.switch_port))
            switches[monitor.dpid].connection.send(msg)

    topo_conf()
    # install_r_flow()
    install_SDN_path()
    # log.debug(path_id)
    with open("id_path.txt", "w") as f:
        # 将每条路径的udp端口号和路径写入文件，udphandler.py根据这个区分不同测量路径
        f.write("id_path:\n")
        for p in path_id.keys():
            f.write("%6s -> " % path_id[p])
            f.write("%s " * len(p) % p)
            f.write("\n")

def _build_monitoring_topo(monitor):

    from readtopo import readtopo
    links, monitors, paths, adj_path = readtopo()
    log.debug('build monitor')
    _install_monitoring_path(monitor, monitors, paths, links, adj_path)

class Monitoring (object):        
    def __init__ (self):
        log.debug("Monitoring coming up")
        def startup():
            # 监听_handle_LinkEvent事件
            core.openflow_discovery.addListeners(self)
            # 监听_handle_ConnectionUp事件
            core.openflow.addListeners(self)
            # 监听_handle_NewMonitor事件
            core.opennetmon_handle_PacketIn.addListeners(self)
            log.debug("Monitoring started")
        core.call_when_ready(startup, 'opennetmon_handle_PacketIn') #Wait for opennetmon-forwarding to be started

    def _handle_ConnectionUp (self, event):
        switches[event.connection.dpid] = event
      
    def _handle_NewMonitor(self, event):
        log.debug("_handle_NewMonitor")
        _build_monitoring_topo(event)
    
    def _handle_LinkEvent(self, event):
        link = event.link
        if event.added:
            adj[link.dpid1][link.dpid2] = link.port1
            
def launch ():
    # 注册Monitoring组件
    core.registerNew(Monitoring)

