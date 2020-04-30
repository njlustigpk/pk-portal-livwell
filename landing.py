import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objects as go
import pymysql
from flask import Flask


e_config = {
    'orgID': 4,
    'growID': 4,
}
def connect_to_cult_RDS():
    conn = pymysql.connect(
        host='cultivation.cjietytfibnb.us-west-1.rds.amazonaws.com',
        user='root',
        password='Illlauren94!',
        db='cultivation',
    )
    c = conn.cursor()
    return conn, c

def get_df():
    testsq = 'SELECT * FROM test WHERE grow_growID = %s'
    c.execute(testsq, (e_config['growID']))
    tests_frame = c.fetchall()
    col_list = ['testID', 'testDate_testDateID', 'grow_growID', 'spore_sporeID', 'sporeCount', 'room_roomID']
    df = pd.DataFrame(tests_frame, columns=col_list, dtype='int')
    return df

def get_viable_spores():
    # get list of viable spores
    q = 'SELECT * FROM spore'
    c.execute(q)
    sporetup = c.fetchall()
    spores = pd.DataFrame(sporetup, columns=['sporeID', 'sporeName', 'viable'])
    #cast first and last col to int
    #spores.loc[:, ['sporeID', 'viable']] = spores.loc[:, ['sporeID', 'viable']].astype(int)
    viable = [id for id, sporeName, viable in sporetup if viable == 1]
    return spores, viable

def get_rooms():
    q = 'SELECT roomID, roomName FROM room WHERE grow_growID = %s'
    c.execute(q, (e_config['growID']))
    roomtup = c.fetchall()
    rooms = pd.DataFrame(roomtup, columns=['roomID', 'roomName'])
    return rooms

def get_tests():
    q = 'SELECT testDateID, date FROM testdate WHERE grow_growID = %s'
    c.execute(q, (e_config['growID']))
    testtup = c.fetchall()
    tests = pd.DataFrame(testtup, columns = ['testDateID', 'date'])
    return tests

# get a list of traces
def get_traces(sdate, edate, room='All Rooms', radio='All Spores'):
    traces = {}
    tf = df
    #subset df to get only the rows for the rooms and spores selected
    if room!='All Rooms':
        roomid = rooms[rooms['roomName']==room]['roomID'].values[0]
        #get only rows that match the roomID
        tf = tf[tf['room_roomID']==roomid]
    if radio=='High TYM Risk Spores':
        #get only rows that are viable
        tf = tf[tf['spore_sporeID'].isin(viable)]

    #populate traces dict
    for spore in tf['spore_sporeID'].unique():
        for test in tf['testDate_testDateID'].unique():
            date = tests[tests['testDateID']==test]['date'].values
            date = list(date)[0] if len(list(date))>0 else date
            if (sdate<=date) & (edate>=date):
                tff = tf[(tf['testDate_testDateID']==test) & (tf['spore_sporeID']==spore)]
                if spore in traces.keys():
                    traces[spore].append({'testDate': date, 'sporeCount': tff['sporeCount'].sum()})
                else:
                    traces[spore] = [{'testDate': date, 'sporeCount': tff['sporeCount'].sum()}]
    return traces

def update_linegraph(fig, traces, room='All Rooms'):
    for trace in traces.keys():
        counts = [t['sporeCount'] for t in traces[trace]]
        if max(counts) > 200:
            #sort by date
            traces[trace] = sorted(traces[trace], key=lambda i: i['testDate'])
            dates = [t['testDate'] for t in traces[trace]]
            name = spores[spores['sporeID']==trace]['sporeName'].values[0]
            fig.add_trace(go.Scatter(x=dates, y=counts, mode='lines+markers', name=name))
    t = 'Spore Count in ' + room
    fig.update_layout(
        title=t,
        xaxis_title='Date',
        yaxis_title='Spore Count (CFUI/M3)'
    )
    return fig


conn, c = connect_to_cult_RDS() #connect to the cult DB

df = get_df()

#get spores and rooms DFs, a list of viable sporeIDs
spores, viable = get_viable_spores() #viable is a list of the viable sporeIDs

rooms = get_rooms()

tests = get_tests()
conn.close()

traces = get_traces(tests.date.min(), tests.date.max())

fig = update_linegraph(go.Figure(), traces)


server = Flask(__name__)
application = dash.Dash(__name__, server=server)

application.layout = html.Div([
    dcc.Graph(
        id='landing-graph',
        figure=fig
    )
], className='root')

if __name__ == '__main__':
    application.run_server(debug=True)