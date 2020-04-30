import pandas as pd
import numpy as np

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

master_db_loc = r"C:\Users\NoahLustig\ProKure Solutions Dropbox (1)\Cultivation\Bio Pump Program\Bio Pump Phase 1\MASTER Bio Pump Database.xlsx"
viable_loc = r"C:\Users\NoahLustig\pkportal\apps\livwell\Original\viable.xlsx"
master_df = pd.read_excel(master_db_loc, sheet_name='MASTER')
viable = pd.read_excel(viable_loc)
viable.index = viable['spore']
viable.drop(['spore'], axis=1, inplace=True)

#delete unnecessary columns
master_df.drop(['Control ID', 'Parent Name', 'ZIP Code', 'Grow Type', 'Soil Type', 'Sample #', 'Room Name', 'Room Type',
                'Comments', 'Using PK', 'Week of test', 'Before', 'After', 'Room Stage', 'Plant Age'], axis=1, inplace=True)

#filter to only livwell rows
master_df = master_df[master_df['Account Name']=='LivWell']

#rename cols
master_df = master_df.rename(columns={'Account Name':'company', 'Sample ID': 'room'})

#fill NaNs with
master_df = master_df.fillna(0)

#melt spores into spores and count columns
col_list = list(master_df.columns)[3:]
meltMast = pd.melt(master_df, id_vars=['Date', 'company', 'room'], value_vars=col_list, var_name='spore', value_name='count')

#drop company
meltMast = meltMast.drop(['company'], axis=1)



#pivot to get dates on cols, reset index
pivoted = meltMast.pivot_table(columns='Date', values='count', index=['spore', 'room'], aggfunc=np.sum, fill_value=0).reset_index()

#remove empty room rows
pivoted = pivoted[pivoted['room']!=' ']
pivoted = pivoted.sort_values(by=['room', 'spore'])
pivoted = pivoted.merge(viable, how='left', on='spore')
pivoted['viable'] = pivoted['viable'].fillna('Low')

pivoted.to_excel('rooms.xlsx')