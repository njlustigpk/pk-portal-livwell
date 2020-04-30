import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
import pymysql
from datetime import datetime, date, timedelta
import numpy as np
from flask import Flask


#set pandas display options
pd.options.display.max_rows = None
pd.options.display.max_columns = None


e_config = {
    'orgID': 4,
    'growID': 4
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

def update_boxplot(fig, traces, room='All Rooms'):
    for trace in traces.keys():
        counts = [t['sporeCount'] for t in traces[trace]]
        if max(counts) > 200:
            #sort by date
            traces[trace] = sorted(traces[trace], key=lambda i: i['testDate'])
            dates = [t['testDate'] for t in traces[trace]]
            name = spores[spores['sporeID']==trace]['sporeName'].values[0]
            fig.add_trace(go.Box(y=counts, name=name))

    t = 'Spore Count Distribution by Spore in ' + room
    fig.update_layout(
        title=t,
        xaxis_title='Spore Name',
        yaxis_title='Spore Count (CFU/M3)'
    )
    return fig

def update_piefig(fig, traces, room='All Rooms'):
    pie = {}
    for trace in traces.keys():
        counts = [t['sporeCount'] for t in traces[trace]]
        if max(counts) > 200:
            #sort by date
            traces[trace] = sorted(traces[trace], key=lambda i: i['testDate'])
            name = spores[spores['sporeID']==trace]['sporeName'].values[0]
            pie[name]=sum(counts)
    #sort pie by labels
    pie2 = {}
    for k, v in sorted(pie.items()):
        pie2[k]=v
    labels = list(pie2.keys())
    values = list(pie2.values())
    t = 'Spores Found in '+ room
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, sort=False)])
    fig.update_traces(hoverinfo='label+value', textinfo='percent')
    fig.update_layout(title=t)
    return fig

def get_spores_table(traces, spores):
    spore_table = pd.DataFrame()
    for sporeid, tlist in traces.items():
        sporeName = spores.loc[spores['sporeID']==sporeid,'sporeName'].values[0]
        spore_table = spore_table.append(pd.DataFrame(dict({'Spore Name':[sporeName]}, **{t['testDate'].strftime('%m/%d/%Y'):[t['sporeCount']] for t in tlist})), ignore_index=True)

    print(spore_table.columns)
    return spore_table


conn, c = connect_to_cult_RDS() #connect to the cult DB

df = get_df()

#get spores and rooms DFs, a list of viable sporeIDs
spores, viable = get_viable_spores() #viable is a list of the viable sporeIDs

rooms = get_rooms()

tests = get_tests()
conn.close()


traces = get_traces(tests.date.min(), tests.date.max())
spore_table = get_spores_table(traces, spores)

linfig = update_linegraph(go.Figure(), traces)

boxfig = update_boxplot(go.Figure(), traces)

piefig = update_piefig(go.Figure(), traces)

server = Flask(__name__)
application = dash.Dash(__name__, server=server)



rooms_list = list(rooms['roomName'])
rooms_list.append('All Rooms')


application.layout = html.Div(children=[
    html.Div([
        html.Div([
            html.Div([
                #lets you choose the room's data that you want displayed on the graph
                dcc.Dropdown(
                    id='rooms-dropdown',
                    options = [{'label': room, 'value': room} for room in rooms_list],
                    multi=False,
                    value='All Rooms'
                )
            ], className='dropdown-container'),
            html.Div([
                #lets you choose to see all spores or only high TYM risk ones
                dcc.RadioItems(
                    id='rooms-radios',
                    options = [{'label': 'All Spores', 'value': 'All Spores'},
                               {'label': 'High TYM Risk Spores', 'value': 'High TYM Risk Spores'}],
                    value='All Spores'
                )
            ], className='radio-container'),
            html.Div([
                dcc.DatePickerRange(
                    id='date-picker',
                    min_date_allowed = tests.date.min(),
                    max_date_allowed = tests.date.max()+timedelta(days=365),
                    initial_visible_month = tests.date.max(),
                    start_date=tests.date.min(),
                    end_date=tests.date.max()
                )
            ], className='date-container')
        ], className='input-container')
    ], className='input-div-container'),
    dcc.Tabs([
        dcc.Tab([
            html.Div([
                html.Div([
                    html.Div([
                            dcc.Graph(
                                id='rooms',
                                figure = linfig,
                                className='fig',
                                config={'displaylogo': False,
                                        'modeBarButtonsToRemove': ['lasso2d']}
                            ),
                    ], className='graph-container')
                ], className='line-chart-container'),
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id='boxplot',
                            figure = boxfig,
                            className='fig',
                            config={'displaylogo': False}
                        )
                    ], className='boxplot-container'),
                    html.Div([
                        dcc.Graph(
                            id='piechart',
                            figure=piefig,
                            className='fig',
                            config={'displaylogo': False}
                        ),
                    ], className='pie-chart-container')
                ], className='spore-charts-container')
            ], className='tab-root')
        ], label='Graphs'),
        dcc.Tab([
            html.Div([
                html.Div([
                    dt.DataTable(
                        id='spore-table',
                        columns = [{'name':i, 'id':i, 'type':'numeric'} for i in spore_table.columns],
                        data = spore_table.to_dict('records'),
                        style_data_conditional=([{
                                'if': {
                                    'column_id': str(c),
                                    'filter_query': '{{{0}}} > 10 && {{{0}}} < 400'.format(c)
                                },
                                'backgroundColor': '#8ff765'
                            } for c in list(spore_table.columns)[1:]] +
                            [{
                                'if': {
                                    'column_id': str(c),
                                    'filter_query': '{{{0}}} > 399 && {{{0}}} <1000'.format(c)
                                },
                                'backgroundColor': '#f5f376'
                            } for c in list(spore_table.columns)[1:]] +
                            [{
                                'if': {
                                    'column_id': str(c),
                                    'filter_query': '{{{0}}} > 999 && {{{0}}} <1999'.format(c)
                                },
                                'backgroundColor': '#f5b649'
                            } for c in list(spore_table.columns)[1:]] +
                            [{
                                'if': {
                                    'column_id': str(c),
                                    'filter_query': '{{{0}}} > 2000'.format(c)
                                },
                                'backgroundColor': '#e0584f'
                            } for c in list(spore_table.columns)[1:]]
                        ),
                        style_data = {
                            'border':'1px solid grey',
                            'minWidth':'150px'
                        },
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold',
                            'border':'2px solid grey',
                        },
                        sort_action='native',
                        filter_action='native',
                        fixed_columns={'headers': True, 'data':1},
                        fixed_rows={'headers': True, 'data':0}
                    )
                ], className='dt-container')
            ], className='tab-root')
        ], label='Data Table')
    ])


], className='container')




#update table
@application.callback(
    [Output('spore-table', 'data'),
     Output('spore-table', 'columns'),
     Output('spore-table', 'style_data_conditional'),
     Output('rooms', 'figure'),
     Output('boxplot', 'figure'),
     Output('piechart', 'figure')],
    [Input('rooms-dropdown', 'value'),
     Input('rooms-radios', 'value'),
     Input('date-picker', 'start_date'),
     Input('date-picker', 'end_date')]
)
def update(room ,radio, sdate, edate):
    sdate = datetime.strptime(sdate, '%Y-%m-%d').date()
    edate = datetime.strptime(edate, '%Y-%m-%d').date()
    t4 = get_traces(sdate, edate, room, radio)
    lin = update_linegraph(go.Figure(), t4, room)
    boxfig = update_boxplot(go.Figure(), t4, room)
    pie = update_piefig(go.Figure(), t4, room)
    sporetable = get_spores_table(t4, spores)
    return sporetable.to_dict('records'), [{'id':'Spore Name', 'name':'Spore Name', 'type':'text'}]+[{'id':c, 'name':c, 'type':'numeric'} for c in list(sporetable.columns)[1:]], \
    ([{
        'if': {
            'column_id': str(c),
            'filter_query': '{{{0}}} > 10 && {{{0}}} < 400'.format(c)
        },
        'backgroundColor': '#8ff765'
    } for c in list(sporetable.columns)[1:]] +
     [{
         'if': {
             'column_id': str(c),
             'filter_query': '{{{0}}} > 399 && {{{0}}} <1000'.format(c)
         },
         'backgroundColor': '#f5f376'
     } for c in list(sporetable.columns)[1:]] +
     [{
         'if': {
             'column_id': str(c),
             'filter_query': '{{{0}}} > 999 && {{{0}}} <1999'.format(c)
         },
         'backgroundColor': '#f5b649'
     } for c in list(sporetable.columns)[1:]] +
     [{
         'if': {
             'column_id': str(c),
             'filter_query': '{{{0}}} > 2000'.format(c)
         },
         'backgroundColor': '#e0584f'
     } for c in list(sporetable.columns)[1:]]
     ), lin, boxfig, pie


if __name__ == '__main__':
    application.run_server()