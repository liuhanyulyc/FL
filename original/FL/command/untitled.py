#!/usr/bin/env python
#-*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import random
import pickle
import sys

from collections import namedtuple
sys.path.append("..")
import readtopo

Link = namedtuple("Link", "delay loss delay_list loss_list")

monitors, SDN_node, paths, links = readtopo.readtopo()

output = open("data.pkl", "w")
n = 6;
data = {}

for j in range(len(links)):
    delay = random.uniform(5,10)
    delay_list = [random.expovariate(1.0/delay)+3 for i in range(n)]
    loss_list = [random.randint(1, 5) for i in range(n)]
    loss = sum(loss_list)/len(loss_list)
    data[links[j]] = Link(delay=delay, delay_list=delay_list, loss=loss, loss_list=loss_list)
    plt.figure(1)
    plt.plot(delay_list, '.-') 
    plt.figure(2)
    plt.plot(loss_list, '*-')

pickle.dump(data, output)
plt.show()