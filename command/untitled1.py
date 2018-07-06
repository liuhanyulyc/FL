#!/usr/bin/env python
#-*- coding: utf-8 -*-


import pickle
import matplotlib.pyplot as plt

from collections import namedtuple
Link = namedtuple("Link", "delay loss delay_list loss_list")
with open("data.pkl", "r") as f:
    data = pickle.load(f)
for k in data:
    delay = data[k].delay
    delay_list = data[k].delay_list[:6]
    loss = data[k].loss
    loss_list = data[k].loss_list[:6]
    plt.figure(1)
    plt.plot(delay_list, '.-') 
    plt.figure(2)
    plt.plot(loss_list, '*-')
plt.show()