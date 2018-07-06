#!/bin/bash/env python
#-*- coding: utf-8 -*-

def readtopo():
    """
    解析result.txt文件，读入topo信息
    """
    import os
    from collections import defaultdict
    from collections import namedtuple

    links = []
    monitors =[]
    paths = []
    f = open(os.path.dirname(__file__) + "/" + 'result.txt', 'r')
    line = f.readline()
    while line:
        if line.find("Monitor") != -1:
            line = f.readline()
            while line.find("Paths"):
                # print line
                x = line.strip().split()
                monitors.append(int(x[1]) + 1)
                line = f.readline()
            # print 'monitors:' + str(monitors)

        elif line.find("Paths") != -1:
            line = f.readline()
            while line.find('Links'):
                # print(line),
                x = line.strip().split(':')
                x1 = x[0].split('-')
                x2 = x[1].split()
                x2 = [int(p)+1 for p in x2]
                # x = [int(p)+1 for p in x]
                paths.append(tuple(x2))
                line = f.readline()
            # print 'paths:' + str(paths)

        elif line.find("Links") != -1:
            line = f.readline()
            while line:
                x = line.split()
                x = [int(p) + 1 for p in x]
                if (x[0], x[1]) not in links and (x[1], x[0]) not in links:
                    links.append((x[0], x[1]))
                line = f.readline()
            # print 'links:' + str(links)
    f.close()

    adj_path = defaultdict(lambda: defaultdict(lambda: []))
    for p in paths:
        if len(p) == 2:
            adj_path[p[0]][p[1]] = adj_path[p[0]][p[1]]
        else:
            adj_path[p[0]][p[1]].append(p[2])
    # for k in adj_path.keys():
    #     for l in adj_path[k].keys():
    #         print k,l
    #         print adj_path[k][l]
    # print adj_path

    return links, monitors, paths, adj_path

from collections import defaultdict
from heapq import *

def dijkstra(edges, f, t):
    g = defaultdict(list)
    for l,r,c in edges:
        g[l].append((c,r))

    q, seen = [(0,f,())], set()
    while q:
        (cost,v1,path) = heappop(q)
        if v1 not in seen:
            seen.add(v1)
            path = (v1, path)
            if v1 == t: return (cost, path)

            for c, v2 in g.get(v1, ()):
                if v2 not in seen:
                    heappush(q, (cost+c, v2, path))

    return float("inf")

def reversePath(src, dst):
    edges = [
        ("0", "2", 1), ("2", "0", 1),  # 1th
        ("0", "6", 1), ("6", "0", 1),  # 2th
        ("0", "15", 1), ("15", "0", 1),  # 3th
        ("1", "3", 1), ("3", "1", 1),  # 4th
        ("1", "6", 1), ("6", "1", 1),  # 5th
        ("1", "11", 1), ("11", "1", 1),  # 6th
        ("1", "12", 1), ("12", "1", 1),  # 7th
        ("1", "17", 1), ("17", "1", 1),  # 8th
        ("1", "22", 1), ("22", "1", 1),  # 9th
        ("2", "9", 1), ("9", "2", 1),  # 10th
        ("2", "20", 1), ("20", "2", 1),  # 11th
        ("4", "7", 1), ("7", "4", 1),  # 12th
        ("5", "6", 1), ("6", "5", 1),  # 13th
        ("7", "8", 1), ("8", "7", 1),  # 14th
        ("10", "2", 1), ("2", "10", 1),  # 15th
        ("10", "9", 1), ("9", "10", 1),  # 16th
        ("11", "9", 1), ("9", "11", 1),  # 17th
        ("11", "21", 1), ("21", "11", 1),  # 18th
        ("12", "13", 1), ("13", "12", 1),  # 19th
        ("12", "16", 1), ("16", "12", 1),  # 20th
        ("12", "18", 1), ("18", "12", 1),  # 21th
        ("13", "2", 1), ("2", "13", 1),  # 22th
        ("14", "8", 1), ("8", "14", 1),  # 23th
        ("14", "19", 1), ("19", "14", 1),  # 24th
        ("15", "3", 1), ("3", "15", 1),  # 25th
        ("15", "4", 1), ("4", "15", 1),  # 26th
        ("15", "8", 1), ("8", "15", 1),  # 27th
        ("15", "9", 1), ("9", "15", 1),  # 28th
        ("16", "6", 1), ("6", "16", 1),  # 29th
        ("16", "9", 1), ("9", "16", 1),  # 30th
        ("16", "19", 1), ("19", "16", 1),  # 31th
        ("16", "22", 1), ("22", "16", 1),  # 32th
        ("17", "20", 1), ("20", "17", 1),  # 33th
        ("18", "5", 1), ("5", "18", 1),  # 34th
        ("18", "6", 1), ("6", "18", 1),  # 35th
        ("19", "21", 1), ("21", "19", 1),  # 36th
        ("20", "6", 1), ("6", "20", 1)  # 37th
    ]
    out = dijkstra(edges, src, dst)
    data = {}
    data['cost'] = out[0]
    aux = []
    while len(out) > 1:
        aux.append(out[0])
        out = out[1]
    aux.remove(data['cost'])
    aux.reverse()
    data['path'] = aux
    a = data
    return data['path']


if __name__ == '__main__':
    links, monitors, paths, adj_path = readtopo()
    # readtopo()