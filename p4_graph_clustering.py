import igraph as ig
import matplotlib.pyplot as plt
import os
import pandas as pd
import leidenalg as la
import configparser
import sqlalchemy
from tqdm import tqdm
import mysql.connector
import json

config = configparser.ConfigParser()
config.read('config.ini')

profile_num = int(config['clustering']['profile_num'])
threshold_follower = int(config['clustering']['threshold_follower'])
threshold_count = int(config['clustering']['threshold_count'])
threshold_percentage = float(config['clustering']['threshold_percentage'])
threshold_percentage_reverse = float(config['clustering']['threshold_percentage_reverse']) # 这个暂时没用到，hard-code

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

def data_selection(df, threshold=[2000,20,0.04]):
    '''function to select data based on threshold
    threshold = [followers, count, percentage]
    '''
    data = df[(df['followers'] >= threshold[0]) & (df['followers_dst'] >= threshold[0])]
    data = data[(data['count'] >= threshold[1])]
    data = data[(data['percentage'] >= threshold[2])]
    # data = data[(data['percentage'] >= 0.04) | (data['percentage_reverse'] >= 0.04)]
    # data = data[(data['percentage']>0.05) & (data['percentage_inv']>0.05)]
    # data = data[(data['percentage']>0.05) | (data['percentage_inv']>0.05)]
    # data = data[['src','dst','count','percentage']]
    return data

def CPM_summary(profile, savepath=""):
    '''function to plot the summary of CPM clustering
    profile: the profile of CPM clustering,
    return: a dictionary of the summary
        - 'resolution': the resolution parameter
        - 'num_communities': the number of communities
        - 'modularity': the modularity, must be y-axis
        - 'index': the index of the profile'''

    num_communities = [len(p) for p in profile]
    modularity = [p.modularity for p in profile]
    resolution = [p.resolution_parameter for p in profile]
    index = list(range(len(profile)))
    dict_summary = {'index': index,
                    'num_communities':num_communities, 'modularity':modularity, 'resolution':resolution,}

    fig, axs = plt.subplots(2, 2)
    fig.set_size_inches(8, 4)
    axs[0, 0].plot(resolution, num_communities)
    axs[0, 0].set(xlabel='resolution', ylabel='num_communities')
    axs[0, 0].set_title('Resolution vs Number of communities')
    axs[0, 1].plot(index, modularity)
    axs[0, 1].set_title('Modularity')
    axs[0, 1].set(xlabel='index', ylabel='modularity')
    axs[1, 0].plot(resolution, modularity)
    axs[1, 0].set_title('Resolution vs Modularity')
    axs[1, 0].set(xlabel='resolution', ylabel='modularity')
    axs[1, 1].plot(index, num_communities)
    axs[1, 1].set_title('Number of communities')
    axs[1, 1].set(xlabel='index', ylabel='num_communities')
    plt.tight_layout()

    if savepath:
        plt.savefig(savepath)
        print(f"Save CPM Summary figure to {savepath}.")
    else:
        plt.show()

    print("Number of communities: ", len(profile))
    return dict_summary

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

# 均匀取n个分区
def _get_partition(profile, n=10):
    total_len = len(profile)
    step = total_len // n
    profile_index = [i for i in range(0, total_len, step)]
    lastone = total_len - 2
    if lastone not in profile_index:
        profile_index.append(lastone)
    return profile_index

def _get_nodes(df):
    df_node = df[df['category'].notna()][['src','followers','category']].drop_duplicates()
    df_node['id'] = df.src.map(name_map_reverse)
    # df_node = df_node.reset_index(drop=True)
    df_node = df_node[['id','src','followers','category']]
    df_node.columns = ['id','name','value','category']
    return df_node

def _get_edges(df):
    df_edge = df[df['category'].notna()][['src','dst','percentage']].drop_duplicates()
    df_edge['source'] = df_edge.src.map(name_map_reverse)
    df_edge['target'] = df_edge.dst.map(name_map_reverse)
    df_edge = df_edge[['source','target','percentage','src','dst']]
    df_edge.columns = ['source','target','weight','src','dst']
    df_edge = df_edge[df_edge['target'].notna()]
    # df_edge = df_edge[df_edge['weight']>0.025]
    return df_edge

def upload_result_toMysql(df, cfg, datestamp, flag=False):
    '''function to upload result to mysql
    df: dataframe of the result
    cfg: config of mysql
    datestamp: datestamp of the result
    flag: True for upload, False for download
    '''
    if flag:
        try:
            engine = sqlalchemy.create_engine(f"mysql+pymysql://{cfg['User']}:{cfg['Password']}@{cfg['Host']}:{cfg['Port']}/{cfg['Database']}")
            # write dataframe to mysql
            df.to_sql(f'result_{datestamp}', engine, if_exists='replace', index=False)
            print(f"Write to mysql successfully! {len(df)} records")
        except Exception as e:
            print(f"Error on upload result to Mysql: {e}")
        finally:
            engine.dispose()
            print("Close connection.")
        return 1
    else:
        # data = pd.read_sql('result', engine)
        # read mysql to dataframe
        print(f"本次运行没有将result数据写入数据库。")
        return 0
    
def upload_clusterJson_toMysql(my_dict, cfg, datestamp, flag=False):
    if flag:
        try:
            mydb = mysql.connector.connect(
                host = cfg['Host'],       # 数据库主机地址
                user = cfg['User'],    # 数据库用户名
                passwd = cfg['Password'],   # 数据库密码
                database = cfg['Database'],
                auth_plugin = 'mysql_native_password'
            )
            mycursor = mydb.cursor()

            # create a table that support json format data in database, then insert dict into the table
            # table with auto-increment index
            mycursor.execute(f"CREATE TABLE IF NOT EXISTS group_{datestamp} (id INT AUTO_INCREMENT PRIMARY KEY, jsondoc JSON)")

            cnt = 0
            for i in my_dict.items():
                sql = "INSERT INTO group_{} (jsondoc) VALUES (%s)".format(datestamp)
                val = (json.dumps(i[1]),)
                mycursor.execute(sql, val)
                mydb.commit()
                cnt += 1
            
            print(f"Total {len(my_dict.items())} partition conditions, {cnt} records inserted.")
        except Exception as e:
            print(f"Error on upload clusterJson to Mysql: {e}")
        finally:
            mycursor.close()
            mydb.close()
            print("Close connection.")
        return 1
    else:
        ## read data from database
        # mycursor.execute("SELECT * FROM group20230212")
        # myresult = mycursor.fetchall()
        # a = json.loads(myresult[0][0])
        # print(a.keys())
        print(f"本次运行没有将clusterJson数据写入数据库。")
        return 0    
    

if __name__ == '__main__':
    today = pd.Timestamp.today().strftime('%Y%m%d')
    print(today)

    ####### Step 1: 数据筛选 #######

    df = pd.read_csv("data/result.csv")
    df = data_processing(df)
    data = data_selection(df, threshold=[threshold_follower, threshold_count, threshold_percentage])
    print(data)

    ## 上传筛选后的数据到数据库
    upload_result_toMysql(data, config['mysql_server'], today, flag=True)

    ####### Step 2: 生成网络并聚类 #######

    ## create graph
    print("Number of nodes: ", len(data['src'].unique()))
    tuples = [tuple(x) for x in data[['src','dst','percentage']].values]
    Gm = ig.Graph.TupleList(tuples, directed = True, edge_attrs = ['percentage'])

    ## Clustering by default method
    partition = la.find_partition(Gm, la.ModularityVertexPartition)

    ### Show clustering with different colors
    ig.plot(partition, "data/plot/clustering_color.png", bbox = (800, 800), vertex_label_dist=1, vertex_label_size=8,
            vertex_size=5, vertex_color=partition.membership,
            edge_width=0.5, edge_arrow_size=0.5, edge_arrow_width=0.5)

    ### Show clustering with different colors and different sizes
    ig.plot(partition, "data/plot/clustering_color_size.png", bbox = (800, 800), vertex_label_dist=1, vertex_label_size=8,
            vertex_size=[len(c) for c in partition], vertex_color=partition.membership,
            edge_width=0.5, edge_arrow_size=0.5, edge_arrow_width=0.5)

    ## Clustering by CPM (Community Preserving Modularity) using optimiser
    optimiser = la.Optimiser()
    profile = optimiser.resolution_profile(Gm, la.CPMVertexPartition, resolution_range=(0,1))
    _ = CPM_summary(profile, savepath=f"data/plot/CPM_summary_{today}.png")

    ## format data
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

    ## 上传聚类结果到数据库
    upload_clusterJson_toMysql(my_dict, config['mysql_server'], today, flag=True)

    ####### Step 3: 生成可视化数据 #######
    
    ## 保存node和edge信息
    ### Gererate a dictionaries for mapping node name to node id
    name_map = {}
    for v in Gm.vs():
        idx = v.index
        name = v.attributes()['name']
        name_map[idx] = name

    name_map_reverse = dict((v,str(k)) for k,v in name_map.items())

    ## 选出n个分区作为我们的结果
    profile_index = _get_partition(profile, n=20)

    # 创建保存路径
    folder_path = f"visualization/data/{today}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    ## 保存结果
    for idx, selected_index in enumerate(tqdm(profile_index)):
        partition = profile[selected_index]
        df2 = data.copy()
        group_map = {}

        ### Mapping
        for group_id, group in enumerate(partition):
            for member in group:
                group_map[name_map[member]] = str(group_id+1)

        df2['category'] = df2.src.map(group_map)
        df_node = _get_nodes(df2)
        df_edge = _get_edges(df2)
        df_edge['source'] = df_edge['source'].astype(str)
        df_edge['target'] = df_edge['target'].astype(str)
        df_node['id'] = df_node['id'].astype(str)
        df_node['category'] = df_node['category'].astype(int)

        ## Select edges from df_edge
        select_edges = []
        for index,row in df_node.iloc[:].iterrows():
            name = row['name']
            df_row = df_edge.loc[df_edge['src'] == name]

            ### Only select closest 40 edges with weight >= 0.15
            myrow = df_row[df_row['weight']>= 0.15].head(40)
            if myrow.shape[0] < 5:
                ### For nodes weight less than 0.15 edges, select closest 10 edges with weight >= 0.05
                myrow = df_row[df_row['weight']>= 0.02].head(10)
            select_edges.append(myrow)
        
        ## Create final dataframe for selected edges
        df_se = pd.concat(select_edges)
        df_e = df_se[df_se['weight']>=0.025]
        df_e['weight'] = round(df_e['weight'],3)
        
        ## Create final dataframe for selected node
        df_n = df_node[df_node['id'].isin(list(df_e.source))]
        df_n['category'] = df_n['category'] - 1

        ### Normalize value
        # df_n['value'] = np.log2(df_n.value)
        df_n['symbolSize'] = round((df_n.value-df_n.value.min())/(df_n.value.max()-df_n.value.min())*70 + 10, 2)
        df_n = df_n.sort_values(['category','value'],ascending=[True,False])

        ### Remove singleton category
        non_singleton = df_n.category.value_counts()[df_n.category.value_counts()>1].index.to_list()
        df_n = df_n[df_n['category'].isin(non_singleton)]

        ### Get category set
        set_category = set(list(df_n.category))

        ## Save to json
        result_node = df_n.to_dict(orient='records')
        result_edge = df_e[['source','target','weight']].to_dict(orient='records')
        result_category = [{'name':str(i)} for i in set_category]

        mydata = {
            "nodes":result_node,
            "links":result_edge,
            "categories":result_category
        }

        with open(f'visualization/data/{today}/mydata_{selected_index}.json', 'w') as file:
            file.write(json.dumps(mydata, ensure_ascii=False, indent=4))
        
        with open(f'visualization/data/{today}/dataFileList.json', 'w') as file:
            file.write(json.dumps(profile_index, ensure_ascii=False, indent=4))
    
    # Show the final category set
    print(f"In Total: {idx+1} clusters, {len(set_category)} category we have.")