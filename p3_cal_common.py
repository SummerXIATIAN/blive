import os
import pandas as pd
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

fans_type = config['cal_common']['fans_type']

def transDict(dictionary, name_list):
    '''data transformation from dictionary to dataframe'''
    length = len(name_list)
    relationshipMap = {
        'src': [dictionary['name']] * length,
        'dst': name_list,
        'count': dictionary['result'],
        'type': [dictionary['type']] * length,
        'followers': [dictionary['followers']] * length
    }
    return relationshipMap

## Get all csv files
directory = f"data/{fans_type}"
all_files = os.listdir(directory)
csv_files = list(filter(lambda f: f.endswith('.csv'), all_files))

## Get all streamers' names
name_list = [f.split(f'_{fans_type}')[0] for f in csv_files]

## Get length
num = len(name_list)

## Calculate common fans for each pair of streamers

### Get all streamers' data
dicts = {}
for index, file in enumerate(csv_files):
    result = []
    try:
        df = pd.read_csv(f"{directory}/{file}")
    except pd.errors.EmptyDataError as e:
        print(f"No content for {index}, {name_list[index]}")
        df = pd.DataFrame(columns=['uid', 'name'],dtype=object)
    dicts[index] = {'name':name_list[index], 'data':df, 'result':result, 'type':fans_type, 'followers':df.shape[0]}

### Calculate common fans
for item in dicts:
    if item % 25 == 0:
        print(f"Processing {item} th, {dicts[item]['name']}")
    for idx in range(len(name_list)):
        # print(item,idx)
        if item == idx:
            dicts[item]['result'].append(0)
            continue
        duplicate_rows = pd.merge(dicts[item]['data'], dicts[idx]['data'], on=['uid'], how='inner')
        cnt = duplicate_rows.shape[0]
        dicts[item]['result'].append(cnt)
        # if cnt > 0:
            # print(item,idx,dicts[item]['name'],dicts[idx]['name'],cnt)
    
    relationshipMap = transDict(dicts[item],name_list)
    # for i in relationshipMap:
        # print(i,len(relationshipMap[i]))
    df_map = pd.DataFrame.from_dict(relationshipMap)
    df_map.to_csv(f"data/result/{dicts[item]['name']}.csv",index=False)

## concat all csv files of streamers to one csv file
dir_path = os.listdir("data/result")    
csv_f = list(filter(lambda f: f.endswith('.csv'), dir_path))

df_all = pd.concat([pd.read_csv(f"data/result/{f}") for f in csv_f], axis=0, ignore_index=True)
df_all = df_all[df_all['count']>0]
df_all['percentage'] = round(df_all['count'] / df_all['followers'], 3)
df_all.to_csv('data/result.csv',index=False)
print("Cal Common Fans -- Done!")