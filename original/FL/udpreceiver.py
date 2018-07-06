#!/usr/bin/env python
#-*- coding: utf-8 -*-

from socket import *
import time
import sys

HOST = '10.0.0.1'
PORT = 10000
BUFSIZ = 1024
ADDR = (HOST, PORT)

udpSerSock = socket(AF_INET, SOCK_DGRAM)
udpSerSock.bind(ADDR)



def main(is_print = None):
    if not is_print:
        udpSerSock.settimeout(10)
        f_delay = open(r'%s.recive'%time.strftime("%Y_%m_%d_%H:%M:%S"), "w")
    try:
        while True:
            data, addr = udpSerSock.recvfrom(BUFSIZ)
            recvtime = time.time()
            if is_print:
                print "%6s %10.4fms"%(addr[1], (recvtime - eval(data)[1])*1000)
                continue
            f_delay.write(repr((addr, data, recvtime))+'\n')
            #f_delay.flush()
    except :
        print "There was a timeout" 
    finally:
        if not is_print:
            f_delay.close()
        udpSerSock.close()
if __name__ == '__main__':
    if len(sys.argv) > 1:
        is_print = True
    else:
        is_print = False
    main(is_print)
