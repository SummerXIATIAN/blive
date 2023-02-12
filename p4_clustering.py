import igraph as ig
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import leidenalg as la
import configparser
import sqlalchemy
from tqdm import tqdm
import mysql.connector
import json

config = configparser.ConfigParser()
config.read('config.ini')

threshold_follower = int(config['clustering']['threshold_follower'])
threshold_count = int(config['clustering']['threshold_count'])
threshold_percentage = float(config['clustering']['threshold_percentage'])

def data_processing(df):
    df = df.sort_values('percentage',ascending=False)
    df = df.reset_index(drop=True)

    ## Add src's & dst's mid information
    df_info = pd.read_csv("data/streamer_info.csv")
    df_info = df_info[['uname','mid']]

    df = pd.merge(df,df_info,how='left',left_on='src',right_on='uname')
    df = pd.merge(df,df_info,how='left',left_on='dst',right_on='uname')

    ## Calculate the reverse of percentage from dst to src
    dict_followers = dict(zip(df.src, df.followers))
    df['followers_dst'] = df['dst'].map(dict_followers)
    df['percentage_reverse'] = df.apply(lambda x: round(x['count'] / dict_followers[x['dst']],3), axis=1)

    ## Rename columns
    df = df[['src', 'dst', 'count', 'type', 'followers', 'percentage', 'percentage_reverse', 'mid_x', 'mid_y','followers_dst']]
    return df

def data_selection(df, threshold=[2000,20,0.05]):
    '''function to select data based on threshold
    threshold = [followers, count, percentage]
    '''
    data = df[(df['followers']>threshold[0]) & (df['followers_dst']>threshold[0])]
    data = data[(data['count']>threshold[1])]
    data = data[(data['percentage']>threshold[2])]
    # data = data[(data['percentage']>0.05) & (data['percentage_inv']>0.05)]
    # data = data[(data['percentage']>0.05) | (data['percentage_inv']>0.05)]
    # data = data[['src','dst','count','percentage']]
    return data


if __name__ == '__main__':
    today = pd.Timestamp.today().strftime('%Y%m%d')
    print(today)

    df = pd.read_csv("data/result.csv")
    df = data_processing(df)
    data = data_selection(df, threshold=[threshold_follower, threshold_count, threshold_percentage])
    print(data)

    ## 用数据库管理
    engine = sqlalchemy.create_engine('mysql+pymysql://xby:zjtzxt123@52.47.199.62:3306/bili')
    # write dataframe to mysql
    data.to_sql(f'result_{today}', engine, if_exists='replace', index=False)
    print(f"write to mysql successfully! {len(data)} records")
    # read mysql to dataframe
    # data = pd.read_sql('result', engine)

    # 生成网络并聚类
    ## create graph
    print("Number of nodes: ", len(data['src'].unique()))
    tuples = [tuple(x) for x in data[['src','dst','percentage']].values]
    Gm = ig.Graph.TupleList(tuples, directed = True, edge_attrs = ['percentage'])

    ## clustering
    partition = la.find_partition(Gm, la.ModularityVertexPartition)

    # ## Show clustering with different colors
    ig.plot(partition, "data/plot/clustering_color.png", bbox = (800, 800), vertex_label_dist=1, vertex_label_size=8,
            vertex_size=5, vertex_color=partition.membership,
            edge_width=0.5, edge_arrow_size=0.5, edge_arrow_width=0.5)

    ## Show clustering with different colors and different sizes
    ig.plot(partition, "data/plot/clustering_color_size.png", bbox = (800, 800), vertex_label_dist=1, vertex_label_size=8,
            vertex_size=[len(c) for c in partition], vertex_color=partition.membership,
            edge_width=0.5, edge_arrow_size=0.5, edge_arrow_width=0.5)

    # ## Clustering by CPM (Community Preserving Modularity) using optimiser
    optimiser = la.Optimiser()
    profile = optimiser.resolution_profile(Gm, la.CPMVertexPartition, resolution_range=(0,1))

    ## format data
    def _get_group(partition):
        '''function to get the group of the partition
        partition: the partition of the graph
        return: a list of the group of the partition'''
        group_info = []
        for idx, g in enumerate(partition):
            info = {}
            info["id"] = f"group_{idx}"
            info["nodes"] = g
            info["size"] = len(g)
            info["names"] = partition.graph.vs[g]['name']
            group_info.append(info)
        return group_info

    my_dict = {}
    for idx, partition in enumerate(tqdm(profile)):
        # print(idx, partition.summary())
        my_dict[idx] = {
            'num_elements': partition.n,
            'num_communities': len(partition),
            'num_edges': partition.graph.ecount(),
            'modularity': partition.modularity,
            'resolution': partition.resolution_parameter,
            'group': _get_group(partition),
            'membership': partition.membership,
            'members': partition.graph.vs['name'],
        }


    mydb = mysql.connector.connect(
    host="52.47.199.62",       # 数据库主机地址
    user="xby",    # 数据库用户名
    passwd="zjtzxt123",   # 数据库密码
    database="bili",
    auth_plugin='mysql_native_password'
    )
    mycursor = mydb.cursor()

    # create a table that support json format data in database, then insert dict into the table
    # table with auto-increment index
    mycursor.execute(f"CREATE TABLE IF NOT EXISTS group_{today} (id INT AUTO_INCREMENT PRIMARY KEY, jsondoc JSON)")

    cnt = 0
    for i in my_dict.items():
        sql = "INSERT INTO group_{} (jsondoc) VALUES (%s)".format(today)
        val = (json.dumps(i[1]),)
        mycursor.execute(sql, val)
        mydb.commit()
        cnt += 1
    
    print(f"Total {len(my_dict.items())} partition conditions, {cnt} records inserted.")

    ## read data from database
    # mycursor.execute("SELECT * FROM group20230212")
    # myresult = mycursor.fetchall()
    # a = json.loads(myresult[0][0])
    # print(a.keys())