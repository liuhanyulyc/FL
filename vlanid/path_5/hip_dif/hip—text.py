from collections import defaultdict, namedtuple

did_path={}
def read_path():
    #读入去除操作延迟的端口号-路径
    f = open('did_path.txt', 'r')
    line = f.readline()
    line = f.readline()
    while line:
        line = line.split("->")
        did_path[int(line[0])] = tuple([int(i) for i in line[1].split()])
        line = f.readline()
    # print 'id_path:' + str(id_path)
    print('did_path' + str(did_path))


    #读入去除操作延迟的端口号——时延
    delay_path_del_list = defaultdict(lambda: defaultdict(lambda: None))
    filename = '2018_06_06_10_47_23.recive'
    with open(filename, 'r') as f:
        line = f.readline()
        # spec = 0
        max_seq = 0

        def parse(line):
            line = line[1:-2].replace('(', ',').replace(')', ',').replace('\'', ',').split(',')
            return int(line[4]), int(line[8]), float(line[9]), float(line[12]),

        while line:
            path, seq, send_time, recive_time = parse(line)
            if seq > max_seq:
                max_seq = seq
            # print path, seq, send_time, recive_time
            if path in did_path.keys():
                delay_path_del_list[path][seq] = (recive_time - send_time) * 1000
            line = f.readline()
            # print seq
    packet_num = max_seq + 1
    print("max_seq:" + str(max_seq))
    print('delay_path_del_list:' + str(delay_path_del_list))
    #计算去除操作后的平均时延，得到端口号-平均时延
    delay_path_del_list_avg={}
    for path in delay_path_del_list.keys():
        sum = 0
        for seq in  range(packet_num):
            sum=sum+delay_path_del_list[path][seq]
            delay_path_del_list_avg[path]=sum/packet_num
    print('delay_path_del_list_avg:'+str(delay_path_del_list_avg))



    #将去除操作时延后的两个列表合一，路径——平均时延
    path_avg_delay_del={}
    for number in did_path.keys():
        for path in  delay_path_del_list_avg.keys():
            if number == path:
                path_avg_delay_del[did_path[number]]=delay_path_del_list_avg[path]
    print('path_avg_delay_del:'+str(path_avg_delay_del))
    print(len(path_avg_delay_del))


    #计算去除操作时延后链路对应的平均时延
    link_avg_delay_del_hip={}
    for path in path_avg_delay_del.keys():
        for path1 in path_avg_delay_del.keys():
            if path==path1[0:-1]:
                link_avg_delay_del_hip[path1[-2],path1[-1],(len(path1))]=path_avg_delay_del[path1]-path_avg_delay_del[path]
    print('link_avg_delay_del_hip：'+str(link_avg_delay_del_hip))
    print(len(link_avg_delay_del_hip))

    #计算跳数与误差的关系
    link_avg_delay_del_hip_dif={}
    for link in link_avg_delay_del_hip.keys():
        link_avg_delay_del_hip_dif[link]=link_avg_delay_del_hip[link]/2 - 10
    print('link_avg_delay_del_hip_dif:'+str(link_avg_delay_del_hip_dif))

    #计算不同跳数的平均误差：
    link_avg_delay_hip_dif_avg={}

    link_avg_delay_hip_dif_avg[2] = 0
    link_avg_delay_hip_dif_avg[3] = 0
    link_avg_delay_hip_dif_avg[4] = 0
    link_avg_delay_hip_dif_avg[5] = 0
    i=[]
    i[0:4]=0,0,0,0
    for link in link_avg_delay_del_hip_dif.keys():
        if link[2]==2:
            link_avg_delay_hip_dif_avg[2] = link_avg_delay_hip_dif_avg[2] + link_avg_delay_del_hip_dif[link]
            i[0]=i[0]+1
        if link[2]==3:
            link_avg_delay_hip_dif_avg[3]=link_avg_delay_hip_dif_avg[3]+link_avg_delay_del_hip_dif[link]
            i[1] = i[1] + 1
        if link[2]==4:
            link_avg_delay_hip_dif_avg[4]=link_avg_delay_hip_dif_avg[4]+link_avg_delay_del_hip_dif[link]
            i[2] = i[2] + 1
        if link[2]==5:
            link_avg_delay_hip_dif_avg[5]=link_avg_delay_hip_dif_avg[5]+link_avg_delay_del_hip_dif[link]
            i[3] = i[3] + 1
    link_avg_delay_hip_dif_avg[2]=link_avg_delay_hip_dif_avg[2]/i[0]
    link_avg_delay_hip_dif_avg[3] = link_avg_delay_hip_dif_avg[3] / i[1]
    link_avg_delay_hip_dif_avg[4]=link_avg_delay_hip_dif_avg[4]/i[2]
    link_avg_delay_hip_dif_avg[5] = link_avg_delay_hip_dif_avg[5] / i[3]
    print(i)
    print('link_avg_delay_hip_dif_avg:'+str(link_avg_delay_hip_dif_avg))







if __name__ == '__main__':
    read_path()
