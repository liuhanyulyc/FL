#!/usr/bin/env python
#-*- coding: utf-8 -*-

from datetime import datetime

def launch ():
        #主程序入口
        from log.level import launch
        launch(DEBUG=True)

        from samples.pretty_log import launch
        launch()

        from openflow.keepalive import launch
        launch(interval=15) # 15 seconds

        #发送LLDP数据包来发现topo
        from openflow.discovery import launch
        launch()

        #等待10.0.0.1的主机发送探测包
        # 检测到10.0.0.1的数据包通知opennetmon.monitoring配置流表
        from FL.forwarding import launch
        launch()

        #配置流表
        from FL.monitoring import launch
        launch()
if __name__ == '__main__':
	launch()
	print("a")
