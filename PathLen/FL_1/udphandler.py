#!/usr/bin/env python2
#-*- coding: utf-8 -*-

import matplotlib  
matplotlib.use('Agg')  
from time import sleep
from math import log, e
import matplotlib.pyplot as plt
import readtopo
import numpy as np
from collections import defaultdict, namedtuple
import pickle
from matplotlib.pyplot import savefig 

Link = namedtuple("Link", "delay loss delay_list loss_list")
import os

id_path = {}
def handle_delay_recive():
    link_n = defaultdict(lambda:defaultdict(lambda:None))
    n = -1
    # 将link从0-->n编号
    for i in id_path.keys():
        p = id_path[i]
        for x in range(len(p)-1):
            if link_n[p[x]][p[x+1]] == None or link_n[p[x+1]][p[x]] == None:
                n = n + 1
                link_n[p[x]][p[x+1]] = link_n[p[x+1]][p[x]] = n
    path_n = {}
    n = -1 
    # 将path从0-->n编号
    for i in id_path.keys():
        n = n + 1
        path_n[i] = n
    import numpy as np
    A = np.matrix([[0.0]*(n+1),]*(n+1))
    # print A
    #根据path构建矩阵
    # print path_n
    for i in id_path.keys():
        path = id_path[i]
        for j in range(len(path)-1):
            A[path_n[i], link_n[path[j]][path[j+1]]] += 1

    #保存矩阵的逆
    A_I = A.I
    delay_path_list = defaultdict(lambda:defaultdict(lambda:None))

    delay_path = np.matrix([0.0]*(n+1)).reshape(-1,1)
    loss_path = np.matrix([0.0]*(n+1)).reshape(-1,1)

    loss = defaultdict(lambda:defaultdict(lambda:0.0))
    filename = '2017_02_16_17:21:02.recive'
    with open(filename, 'r') as f:
        line = f.readline()
        spec = 0
        max_seq = 0;
        def parse(line):
            line = line[1:-2].replace('(', ',').replace(')', ',').replace('\'', ',').split(',')
            return int(line[4]), int(line[8]), float(line[9]), float(line[12]), 
        while line:
            path_id, seq, send_time, recive_time = parse(line)
            if path_id in path_n.keys():
                delay_path_list[path_n[path_id]][seq] = (recive_time - send_time)*1000 - spec
                loss[path_n[path_id]][seq] = 1
            else:
                spec = (recive_time - send_time)*1000
            if seq > max_seq:
                max_seq = seq
            line = f.readline()

    for i in range(max_seq):
        for path_id in path_n.keys():
            loss[path_n[path_id]][i] += loss[path_n[path_id]][i-1]
    
    monitors, SDN_node, paths, links = readtopo.readtopo()

    loss_window_size = 1000
    loss_window_size2 = 100
    delay_window_size = 500*10
    link_loss = defaultdict(lambda:[])
    for i in range(max_seq - loss_window_size):
        i = i + loss_window_size
        for path_id in path_n.keys():
            try:
                loss_path[path_n[path_id]] = log((loss[path_n[path_id]][i] -loss[path_n[path_id]][i-loss_window_size])/(loss_window_size))
            except ValueError, error:
                print loss[path_n[path_id]][i], loss[path_n[path_id]][i-loss_window_size]
                return

        # # 求解link_loss
        link_loss_temp = A_I*loss_path
        for g in path_n.keys():
            # 指数还原之前取的对数
            link_loss_temp[path_n[g],0] = (1 - e**link_loss_temp[path_n[g],0])*100

        for k in links:
            link_loss[k].append(link_loss_temp[link_n[k[0]][k[1]],0])

    link_delay = defaultdict(lambda:[])

    for i in range(max_seq):
        i += 10
        for path_id in path_n.keys():
            k = i;
            while delay_path_list[path_n[path_id]][k] == None and k >=  0:
                k = k -1;
            delay_path[path_n[path_id]] = delay_path_list[path_n[path_id]][k]
            # print delay_path[path_n[path_id]]
        # 求解时延
        a = A_I*delay_path
        for k in links:
            link_delay[k].append(a[link_n[k[0]][k[1]],0])

    offset = 0
    try:
        os.mkdir(filename+".ans")
    except :
        pass

    ans_file = open(filename+".ans"+"/ans.txt", "w")
    with open("command/data.pkl", "r") as f:
        data = pickle.load(f)
        sub_i = 1;
        x = [i/500.0 for i in range(len(link_delay[k]))]
        def conv(link_delay_k):
            temp1 = temp2 = link_delay_k[0]
            link_delay_k[0] = sum(link_delay_k[:200])
            for i in range(len(link_delay_k)-200):
                i = i + 1
                temp1 = link_delay_k[i]
                link_delay_k[i] = link_delay_k[i-1] + link_delay_k[i+199] - temp2
                temp2 = temp1
            link_delay_k = [link_delay_k[i]/200.0 for i in range(len(link_delay_k))]
            return link_delay_k
        for k in link_delay:
            # k = link_delay.keys()[2]
            # plt.subplot(int("%s%s%s"%(len(link_delay.keys())/2+1, 2, sub_i)))
            sub_i = sub_i+1
            link_delay[k] = conv(link_delay[k])
            # plt.plot(x[:len(link_delay[k])], link_delay[k], 'r', label = "measure %s-%s"%(k[0], k[1]))
            ans = [data[k].delay_list[i/(delay_window_size/loss_window_size2)] for i in range(len(link_delay[k])/loss_window_size2)]
            ans += [ans[-1] for i in range(15)]
            ans = ans[15:]
            # plt.plot(x[:len(ans)], ans, 'b', label = "theory %s-%s"%(k[0], k[1]))
            # plt.legend(fontsize = 10)
            # plt.ylim(0, 40)
            # plt.xlabel("time:second")
            # plt.ylabel("delay:ms")
            # plt.title("delay measure")
            # # break;
            # savefig(filename+".ans"+"/%s delay %s-%s.svg"%(filename, k[0], k[1]))
            # plt.clf()
            with open(filename+".ans"+"/delay_%s_%s.csv"%(k[0], k[1]), "w") as w_f:
                #for i in link_delay[k]:
                #    w_f.write('%s\n'%i)
                #continue
                w_f.write("measure,theory\n")
                for col_i in range(min(len(ans), len(link_delay[k]))):
                    w_f.write("%s,%s\n"%(link_delay[k][col_i*loss_window_size2], ans[col_i]))
        #return
        x = [i*loss_window_size/50.0 for i in range(len(link_loss[k][::loss_window_size]))]
        for k in link_loss:
            # k = link_delay.keys()[2]
            # plt.subplot(int("%s%s%s"%(len(link_loss.keys())/2+1, 2, sub_i)))
            # plt.plot(x[:len(link_loss[k][::loss_window_size])], link_loss[k][::loss_window_size][:len(x)], 'r', label = "measure %s-%s"%(k[0], k[1]))
            ans = data[k].loss_list
            ans = [data[k].loss_list[(i*loss_window_size)/delay_window_size] for i in range(len(link_loss[k][::loss_window_size]))]
            ans += [ans[-1] for i in range(2)]
            ans = ans[2:]
            # plt.plot(x[:len(ans)], ans[:len(x)], 'b', label = "theory %s-%s"%(k[0], k[1]))
            # plt.ylim(0, 10)
            # plt.legend(fontsize = 10)
            # plt.xlabel("time:second")
            # plt.ylabel("loss:%")
            # plt.title("loss measure")
            # # break;
            # savefig(filename+".ans"+"/%sloss %s-%s.svg"%(filename, k[0], k[1]))
            # plt.clf()
            with open(filename+".ans"+"/loss_%s_%s.csv"%(k[0], k[1]), "w") as w_f:
                w_f.write("measure,theory\n")
                for col_i in range(min(len(link_loss[k]), len(ans))):
                    w_f.write("%s,%s\n"%(link_loss[k][col_i*loss_window_size], ans[col_i]))


        for k in link_delay:
            try:
                delay_error = [abs(link_delay[k][i] - data[k].delay_list[(i+offset)/delay_window_size])/data[k].delay_list[(i+offset)/delay_window_size] for i in range(len(link_delay[k])-offset)]
            except IndexError:
                print i, i + offset
                print len(link_delay[k])
                return
            loss_error = [abs(link_loss[k][i*delay_window_size+offset] - data[k].loss_list[i])/data[k].loss_list[i] for i in range(len(data[k].loss_list)-1)]
            print >> ans_file, k, "delay_error:%.4lf"%(sum(delay_error)/(len(link_delay[k])-offset)*100), "loss_error:%.4lf"%(100*sum(loss_error)/len(loss_error))
        ans_file.close()

    return

def main():
    # 读入id_path.txt
    f = open('id_path.txt', 'r')
    line = f.readline()
    line = f.readline()
    while line:
        line = line.split("->")
        id_path[int(line[0])] = tuple([int(i) for i in line[1].split()])
        line = f.readline()
    f.close()
    handle_delay_recive()
if __name__ == '__main__':
    main()
