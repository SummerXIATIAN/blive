import igraph as ig
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import leidenalg as la
import configparser

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

def data_selection(df, threshold=[200,20,0.05]):
    '''function to select data based on threshold
    threshold = [followers, count, percentage]
    '''
    data = df[(df['followers']>2000) & (df['followers_dst']>2000)]
    data = data[(data['count']>20)]
    data = data[(data['percentage']>0.05)]
    # data = data[(data['percentage']>0.05) & (data['percentage_inv']>0.05)]
    # data = data[(data['percentage']>0.05) | (data['percentage_inv']>0.05)]
    data = data[['src','dst','count','percentage']]
    return data


if __name__ == '__main__':
    df = pd.read_csv("data/result.csv")
    df = data_processing(df)
    data = data_selection(df, threshold=[threshold_follower, threshold_count, threshold_percentage])
    print(data)

    #### 后面还没有写好，打算灵活调用多个数据