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
    Links = {}
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
        #===================================================================================
        for path in paths:
            for e,node in enumerate(path):
                if node == path[0]:
                    node = int(node)
                    prenode = monitor.dpid
                    nextnode = int(path[e+1])

                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    msg.match.dl_dst, msg.match.dl_src, msg.match.tp_dst = (None,) * 3
                    msg.match.nw_src, msg.match.nw_dst = (None,) *2
                    msg.match.tp_src = path_id[path]
                    msg.match.in_port = adj[node][prenode]
                    msg.actions.append(of.ofp_action_output(port=adj[node][nextnode]))
                    switches[node].connection.send(msg)

                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    msg.match.dl_dst, msg.match.dl_src, msg.match.tp_dst = (None,) * 3
                    msg.match.nw_src, msg.match.nw_dst = (None,) *2
                    msg.match.tp_src = path_id[path]
                    msg.match.in_port = adj[node][nextnode]
                    msg.actions.append(of.ofp_action_output(port=adj[node][prenode]))
                    switches[node].connection.send(msg)
                elif node == path[-1]:
                    node = int(node)
                    prenode = int(path[e-1])
                    # print node
                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    msg.match.dl_dst, msg.match.dl_src, msg.match.tp_dst= (None,) * 3
                    msg.match.nw_src, msg.match.nw_dst = (None,) *2
                    msg.match.tp_src = path_id[path]
                    msg.match.in_port = adj[node][prenode]
                    msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                    switches[node].connection.send(msg)
                else:
                    node = int(node)
                    prenode = int(path[e-1])
                    nextnode = int(path[e+1])

                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    msg.match.dl_dst, msg.match.dl_src, msg.match.tp_dst = (None,) * 3
                    msg.match.nw_src, msg.match.nw_dst = (None,) *2
                    msg.match.tp_src = path_id[path]
                    msg.match.in_port = adj[node][prenode]
                    msg.actions.append(of.ofp_action_output(port=adj[node][nextnode]))
                    # print node
                    switches[node].connection.send(msg)

                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    msg.match.dl_dst, msg.match.dl_src, msg.match.tp_dst = (None,) * 3
                    msg.match.nw_src, msg.match.nw_dst = (None,) *2
                    msg.match.tp_src = path_id[path]
                    msg.match.in_port = adj[node][nextnode]
                    msg.actions.append(of.ofp_action_output(port=adj[node][prenode]))
                    # print node
                    switches[node].connection.send(msg)
#===================================================================================
        #r24收到h1的probe后
        msg = of.ofp_flow_mod()
        msg.match = monitor.match.clone()  
        #匹配h1
        msg.match.tp_dst, msg.match.tp_src = (None,) * 2
        msg.match.nw_src = IPAddr('10.0.0.1')
        msg.match.nw_dst = IPAddr('10.0.0.2')
        msg.match.in_port = monitor.switch_port
        #转发
        for path in paths:
            msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[path]))
            msg.actions.append(of.ofp_action_output(port=adj[monitor.dpid][int(path[0])]))
        switches[monitor.dpid].connection.send(msg)

        #r24收到s2的probe后
        msg = of.ofp_flow_mod()
        msg.match = monitor.match.clone()   
        msg.match.in_port = adj[monitor.dpid][2]
        #匹配
        msg.match.tp_dst, msg.match.tp_src, msg.match.nw_dst, msg.match.nw_src = (None,) * 4
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
    with open("topo.txt", "w") as f:
        for k in adj:
            for j in adj[k]:
                f.write("%s %s %s\n"%(k, j, adj[k][j]))

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

