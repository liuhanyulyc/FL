#!/usr/bin/env python
#-*- coding: utf-8 -*-

"""
向虚拟节点‘10.0.0.2’发送udp数据包，包含发送序列号时间和时间
序列号可用于统计loss rate
"""
from socket import *
import time
import sys

HOST = '10.0.0.2'
PORT = 10000
BUFSIZ = 1024
ADDR = (HOST, PORT)

udpCliSock = socket(AF_INET, SOCK_DGRAM)
udpCliSock.bind(('10.0.0.1', 9999))

internal = 0.002
measure_time = 60
n = int(measure_time/internal)
# n = 2

def main():
    for i in range(n):
        # i += 1
        data = repr((i, time.time()))
        udpCliSock.sendto(data, ADDR)
        if i%500==0:
            print("send %d probe packet."%i)
        time.sleep(internal)
    udpCliSock.close()

if __name__ == '__main__':
    main()
