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

interval = 0.002
time_interval = 0.490
period = 5.0
measure_time = 20
n = int((measure_time/period) * 5 *(period / (interval*5 + time_interval)))
# print n
# n = 1

def main():
    for i in range(n):
        data = repr((i, time.time()))
        udpCliSock.sendto(data, ADDR)
        # if i%500==0:
        #     print("send %d probe packet."%i)
        if i % 5 == 0:
            print("send %d probe packet."%i)
            time.sleep(time_interval - interval)
        time.sleep(interval)
    udpCliSock.close()

if __name__ == '__main__':
    main()
