#!/usr/bin/env python
#-*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import random
import pickle
import sys
import math

from collections import namedtuple
sys.path.append("..")
import readtopo

# Link = namedtuple("Link", "delay loss delay_list loss_list")
Link = namedtuple("Link", "delay delay_list")

links, monitors, paths, adj_path = readtopo.readtopo()

output = open("data.pkl", "w")
# n = 120
data = {}

for j in range(len(links)):
    x = random.uniform(5,10)
    t = 0
    delay_list = []
    for i in range(60):
        delay = (1/x) * math.sin(0.8 * (math.pi)*t)+5.0
        delay_list.append(delay)
        data[links[j]] = Link(delay=delay, delay_list=delay_list)
        t += 0.25
    for i in range(40):
        delay = (1/x) * math.sin(0.6 * (math.pi)*t)+7.0
        delay_list.append(delay)
        data[links[j]] = Link(delay=delay, delay_list=delay_list)
        t += 0.25
    for i in range(80):
        delay = (1/x) * math.sin(0.4 * (math.pi)*t)+6.0
        delay_list.append(delay)
        data[links[j]] = Link(delay=delay, delay_list=delay_list)
        t += 0.25
    for i in range(40):
        delay = (1/x) * math.sin(0.4 * (math.pi)*t)+ 9.0
        delay_list.append(delay)
        data[links[j]] = Link(delay=delay, delay_list=delay_list)
        t += 0.25
    # plt.figure(1)
    # plt.plot(delay_list, '.-') 

pickle.dump(data, output)
# plt.show()