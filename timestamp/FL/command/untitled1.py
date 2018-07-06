#!/usr/bin/env python
#-*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import random
import pickle
import sys

from collections import namedtuple
sys.path.append("..")
import readtopo

Link = namedtuple("Link", "delay delay_list")

links, monitors, paths, adj_path = readtopo.readtopo()

output = open("data.pkl", "w")
n = 6
data = {}
for j in range(len(links)):
    uni_delay = random.uniform(0,10)
    k = random.randint(1,5)
    Lambda = random.uniform(0.1,1)
    delay_list = [random.gammavariate(k,Lambda)+uni_delay for i in range(n)]
    data[links[j]] = Link(delay=uni_delay, delay_list=delay_list)

    # plt.figure(1)
    # plt.plot(delay_list, '.-')

pickle.dump(data, output)
plt.show()