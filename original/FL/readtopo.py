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
            #print 'monitors:' + str(monitors)

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
            #print 'paths:' + str(paths)

        elif line.find("Links") != -1:
            line = f.readline()
            while line:
                x = line.split()
                x = [int(p) + 1 for p in x]
                if (x[0], x[1]) not in links and (x[1], x[0]) not in links:
                    links.append((x[0], x[1]))
                line = f.readline()
            #print 'links:' + str(links)
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
    #print adj_path
    return links, monitors, paths, adj_path

if __name__ == '__main__':
    links, monitors, paths, adj_path = readtopo()
    # readtopo()
