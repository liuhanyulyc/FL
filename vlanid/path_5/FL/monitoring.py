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
    switches_ip, path_id, switches_mac,path_did = {}, {}, {},{}
    #设置路径vlanid值
    for p in monitors:
        c=[]
        c.append(p)
        paths.append(tuple(c))
    j = 3
    paths.append((17,20))
    for p in paths:
        path_did[p] = j
        j = j + 1

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
            
        '''# 将路径补充完整
        for p in monitors:
            c=[]
            c.append(p)
            paths.append(tuple(c))

        j = 1
        for p in paths:
            path_vid[p] = 500 + j
            j = j + 1
        '''
    


    def install_SDN_path():
        #端口 转发
        for p in  path_did.keys():
            #在第一层就返回的情况
            if len(p)==1:
                msg = of.ofp_flow_mod(match=monitor.match.clone())
                msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                msg.match.tp_src = path_did[p]
                msg.match.in_port=adj[p[0]][monitor.dpid]
                msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                switches[p[0]].connection.send(msg)       
            else :
                # 到达第一层交换机
                msg = of.ofp_flow_mod()
                msg.match = monitor.match.clone()
                msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                msg.match.tp_src = path_did[p]
                msg.match.in_port = adj[p[0]][monitor.dpid]
                msg.actions.append(of.ofp_action_output(port=adj[p[0]][p[1]]))
                switches[p[0]].connection.send(msg)
                #从第二层一直到底层的情况
                for n in range(1,len(p)):
                    if n < (len(p)-1):
                        msg=of.ofp_flow_mod()
                        msg.match=monitor.match.clone()
                        msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                        msg.match.tp_src = path_did[p]
                        msg.match.in_port=adj[p[n]][p[n-1]]
                        msg.actions.append(of.ofp_action_output(port=adj[p[n]][p[n+1]]))
                        switches[p[n]].connection.send(msg)
                    else:
                        msg = of.ofp_flow_mod()
                        msg.match = monitor.match.clone()
                        msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                        msg.match.tp_src = path_did[p]
                        msg.match.in_port = adj[p[n]][p[n-1]]
                        msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                        switches[p[n]].connection.send(msg)
               # 返回到一层的操作
                for m in range((len(p)-2),0,-1):
                    msg=of.ofp_flow_mod()
                    msg.match=monitor.match.clone()
                    msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                    msg.match.tp_src = path_did[p]
                    msg.match.in_port=adj[p[m]][p[m+1]]
                    msg.actions.append(of.ofp_action_output(port=adj[p[m]][p[m-1]]))
                    switches[p[m]].connection.send(msg)
                #返回到一层之后,返回到r24
                msg=of.ofp_flow_mod()
                msg.match=monitor.match.clone()
                msg.match.nw_src, msg.match.tp_dst, msg.match.nw_dst = (None,) * 3
                msg.match.tp_src = path_did[p]
                msg.match.in_port=adj[p[0]][p[1]]
                msg.actions.append(of.ofp_action_output(port=adj[p[0]][monitor.dpid]))
                switches[p[0]].connection.send(msg)
            #在达到s24之后的处理
            '''
            msg = of.ofp_flow_mod()
            msg.match = monitor.match.clone()
            msg.match.nw_src=IPAddr('10.0.1.1')
            msg.match.tp_src = path_did[p]
            msg.match.in_port = adj[monitor.dpid][p[0]]
            msg.actions.append(of.ofp_action_nw_addr.set_dst(nw_addr=monitor.ip))
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr=IPAddr('10.0.0.2')))
            msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr=monitor.hw))
            msg.actions.append(of.ofp_action_dl_addr.set_src(dl_addr=EthAddr("00:00:00:00:00:02")))
            msg.actions.append(of.ofp_action_output(port=monitor.switch_port))
            switches[monitor.dpid].connection.send(msg)
            '''              
                




        '''
        #根节点收到上面的probe后
        for node in adj_path.keys():
            msg = of.ofp_flow_mod(match=monitor.match.clone())
            #匹配
            msg.match.tp_dst, msg.match.tp_src = (None,) * 2
            msg.match.nw_src = IPAddr('10.0.0.1')
            msg.match.nw_dst = IPAddr('10.0.0.2')
            msg.match.in_port = adj[node][monitor.dpid]
            #modify ip and 向下转发
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr = switches_ip[node]))
            for nextnode in adj_path[node].keys():
                msg.actions.append(of.ofp_action_output(port=adj[node][nextnode]))
            #修改udp_port,发送回r24
            temp_path = []
            temp_path.append(24)
            temp_path.append(node)
            temp_path = tuple(temp_path)
            msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
            msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
            switches[node].connection.send(msg)

        #第二层节点收到第一层的probe以后
        for node in adj_path.keys():
            for nextnode in adj_path[node].keys():
                msg = of.ofp_flow_mod(match=monitor.match.clone())
                # 匹配
                msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                msg.match.nw_src = switches_ip[node]
                msg.match.nw_dst = IPAddr('10.0.0.2')
                msg.match.in_port = adj[nextnode][node]
                # 向下转发
                for lastnode in adj_path[node][nextnode]:
                    msg.actions.append(of.ofp_action_output(port=adj[nextnode][lastnode]))
                #modify and send back
                temp_path = []
                temp_path.append(24)
                temp_path.append(node)
                temp_path.append(nextnode)
                temp_path = tuple(temp_path)
                msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
                msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                switches[nextnode].connection.send(msg)

        #第三层节点收到probe以后
        for node in adj_path.keys():
            for nextnode in adj_path[node].keys():
                for lastnode in adj_path[node][nextnode]:
                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    # 匹配
                    msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                    msg.match.nw_src = switches_ip[node]
                    msg.match.nw_dst = IPAddr('10.0.0.2')
                    msg.match.in_port = adj[lastnode][nextnode]
                    #转发回去
                    temp_path = []
                    temp_path.append(24)
                    temp_path.append(node)
                    temp_path.append(nextnode)
                    temp_path.append(lastnode)
                    temp_path = tuple(temp_path)
                    msg.actions.append(of.ofp_action_tp_port.set_src(tp_port=path_id[temp_path]))
                    msg.actions.append(of.ofp_action_output(port=of.OFPP_IN_PORT))
                    switches[lastnode].connection.send(msg)

        #第二层节点收到第三层的probe以后
        for node in adj_path.keys():
            for nextnode in adj_path[node].keys():
                for lastnode in adj_path[node][nextnode]:
                    msg = of.ofp_flow_mod(match=monitor.match.clone())
                    # 匹配
                    msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                    msg.match.nw_src = switches_ip[node]
                    msg.match.nw_dst = IPAddr('10.0.0.2')
                    msg.match.in_port = adj[nextnode][lastnode]
                    #往上转发
                    msg.actions.append(of.ofp_action_output(port=adj[nextnode][node]))
                    switches[nextnode].connection.send(msg)

        #第一层节点收到第二层的probe以后
        for node in adj_path.keys():
            for nextnode in adj_path[node].keys():
                msg = of.ofp_flow_mod(match=monitor.match.clone())
                msg.match.tp_dst, msg.match.tp_src = (None,) * 2
                msg.match.nw_src = switches_ip[node]
                msg.match.nw_dst = IPAddr('10.0.0.2')
                msg.match.in_port = adj[node][nextnode]
                #往上转发
                msg.actions.append(of.ofp_action_output(port=adj[node][monitor.dpid]))
                switches[node].connection.send(msg)

                log.debug('monitor num')
        '''

        for node in adj_path.keys():
            msg = of.ofp_flow_mod()
            msg.match = monitor.match.clone()   
            
            #匹配
            msg.match.nw_src,msg.match.tp_dst,msg.match.tp_src,msg.match.nw_dst = (None,) * 4
            #msg.match.nw_src = IPAddr('10.0.0.1')
            #msg.match.nw_dst = IPAddr('10.0.0.2')
            msg.match.in_port = adj[monitor.dpid][node]

            #修改IP
            # msg.actions.append(of.ofp_action_nw_addr.set_dst(nw_addr = IPAddr('10.0.0.2')))
            # msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = EthAddr("00:00:00:00:00:02")))            # msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = EthAddr("00:00:00:00:00:02")))            #向上转发
            msg.actions.append(of.ofp_action_nw_addr.set_dst(nw_addr = monitor.ip))
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr = IPAddr('10.0.0.2')))
            msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = monitor.hw))
            msg.actions.append(of.ofp_action_dl_addr.set_src(dl_addr = EthAddr("00:00:00:00:00:02")))
            msg.actions.append(of.ofp_action_output(port=monitor.switch_port))
            switches[monitor.dpid].connection.send(msg)








        ''' 
        msg = of.ofp_flow_mod()
        msg.match = monitor.match.clone()  
        #匹配h1
        msg.match.tp_dst= None
        msg.match.nw_src = IPAddr('10.0.0.1')
        msg.match.nw_dst = IPAddr('10.0.0.2')
        msg.match.tp_src = 9999
        msg.match.in_port = monitor.switch_port
        print monitor.switch_port
        #转发
        for node in adj_path.keys():
            msg.actions.append(of.ofp_action_output(port=adj[monitor.dpid][node]))

        switches[monitor.dpid].connection.send(msg)
        '''  


        #r24收到h1的probe后(除去操作时延)
        for p in path_did.keys():
            msg = of.ofp_flow_mod()
            msg.match = monitor.match.clone()
            msg.match.tp_dst, msg.match.nw_src, msg.match.nw_dst =(None,) *3
            msg.match.in_port = monitor.switch_port
            msg.match.tp_src=path_did[p]
            msg.actions.append(of.ofp_action_nw_addr.set_src(nw_addr=IPAddr('10.0.1.2')))
            msg.actions.append(of.ofp_action_output(port=adj[monitor.dpid][p[0]]))  
            switches[monitor.dpid].connection.send(msg)
   
        
    # def install_r_flow():
    #     """
    #     Using a r SDN node  send and receive probe packet
    #     """
    #     #r24收到从下面来的probe以后
    #     log.debug('monitor num')
    #     for node in adj_path.keys():
    #         msg = of.ofp_flow_mod()
    #         msg.match = monitor.match.clone()            
    #         #匹配
    #         msg.match.tp_dst, msg.match.tp_src = (None,) * 2
    #         msg.match.nw_src = IPAddr('10.0.0.1')
    #         msg.match.nw_dst = IPAddr('10.0.0.2')
    #         msg.match.in_port = adj[monitor.dpid][node]

    #         #修改IP
    #         msg.actions.append(of.ofp_action_nw_addr.set_dst(nw_addr = IPAddr('10.0.0.2')))
    #         msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = EthAddr("00:00:00:00:00:02")))            # msg.actions.append(of.ofp_action_dl_addr.set_dst(dl_addr = EthAddr("00:00:00:00:00:02")))            #向上转发
    #         msg.actions.append(of.ofp_action_output(port=monitor.switch_port))
    #         switches[monitor.dpid].connection.send(msg)

    #     #r24收到h1的probe后
    #     msg = of.ofp_flow_mod()
    #     msg.match = monitor.match.clone()  
    #     #匹配h1
    #     msg.match.tp_dst, msg.match.tp_src = (None,) * 2
    #     msg.match.nw_src = IPAddr('10.0.0.1')
    #     msg.match.nw_dst = IPAddr('10.0.0.2')
    #     msg.match.in_port = monitor.switch_port
    #     #转发
    #     for node in adj_path.keys():
    #         msg.actions.append(of.ofp_action_output(port=adj[monitor.dpid][node]))
    #     switches[monitor.dpid].connection.send(msg)


    topo_conf()
    # install_r_flow()
    install_SDN_path()
    # log.debug(path_id)
    #with open("id_path.txt", "w") as f:
        # 将每条路径的udp端口号和路径写入文件，udphandler.py根据这个区分不同测量路径
        #f.write("id_path:\n")
        #for p in path_id.keys():
            #f.write("%6s -> " % path_id[p])
            #f.write("%s " * len(p) % p)
            #f.write("\n")
    
    with open("did_path.txt", "w") as m:
        # 将每条路径的vid号和路径写入文件
        m.write("did_path:\n")
        for p in path_did.keys():
            m.write("%6s -> " % path_did[p])
            m.write("%s " * len(p) % p)
            m.write("\n")


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


