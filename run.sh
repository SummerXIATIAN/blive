#!/bin/bash

# 记录开始时间
echo "Start Time: " `date`

# 清空fans下的csv文件
rm -f ./data/fans/*.csv

# 清空result下的csv文件
rm -f ./data/result/*.csv

# 执行p1.py
python ./p1_get_streamers.py

# 执行p2.py
python ./p2_get_fans_group.py

# 执行p3.py
python ./p3_cal_common.py

# 执行p4.py
python ./p4_graph_clustering.py