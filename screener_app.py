import pandas as pd 
import requests 
from bs4 import BeautifulSoup
import yfinance as yf 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np 
import streamlit as st 
import talib as ta 

# App Setup 
#******************************************************************************************************************************************************************************
st.set_page_config(page_title='My Economic Dashboard', page_icon='📊', layout='wide')
st.title('Stock Screener 📝')


# Bring in S&P500 data from Wikipedia
#******************************************************************************************************************************************************************************
def get_sp500_table(): 
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    page = requests.get(url, headers = {'User-agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'})
    soup = BeautifulSoup(page.text, 'lxml')
    table = soup.find('table')

    #get column headers
    headings = table.find_all('th')
    company_table_headings = [title.text.strip() for title in headings] 

    #get column row data 
    scraped_data = [] 
    for row in table.find_all('tr')[1:]:
        row_data = row.find_all('td')
        individual_row_data = [data.text.strip() for data in row_data]
        scraped_data.append(individual_row_data)
        
    df = pd.DataFrame(data=scraped_data, columns=company_table_headings).sort_values(by='Symbol')
    return df


#Create list of all Tickers 
#******************************************************************************************************************************************************************************
def get_sp500_symbols(): 
    df = get_sp500_table() 
    tickers_list = df['Symbol'].to_list() 
    return tickers_list


#Bring in yfinance data 
#******************************************************************************************************************************************************************************
def get_data(ticker, start_date, end_date): 
    data = yf.download(ticker, start=start_date, end=end_date)
    stacked_data = data.stack().reset_index(level='Ticker')
    grouped_df = stacked_data.groupby(['Ticker', 'Date']).sum().reset_index()

    #Create helper column to flag rows where the ticker changes
    grouped_df['Flag'] = np.where(grouped_df['Ticker'] == grouped_df['Ticker'].shift(1), 0, 1)

    #Add 20 & 50 day rolling average
    grouped_df['MA20'] = np.where(grouped_df['Flag'] == 0, grouped_df['Close'].rolling(window=20).mean(), 0)
    grouped_df['MA50'] = np.where(grouped_df['Flag'] == 0, grouped_df['Close'].rolling(window=50).mean(), 0)

    #Calculate RSI 
    grouped_df['Delta'] = grouped_df['Close'].diff() 
    grouped_df['Gain'] = (grouped_df['Delta'].where(grouped_df['Delta'] > 0, 0)).rolling(window=14).mean() 
    grouped_df['Loss'] = (-grouped_df['Delta'].where(grouped_df['Delta'] < 0, 0)).rolling(window=14).mean()
    grouped_df['RS'] = round(grouped_df['Gain'] / grouped_df['Loss'], 2) 
    grouped_df['RSI'] = round(100 - (100 / (1 + grouped_df['RS'])), 2) 
    grouped_df['RSI Signal'] = np.where(grouped_df['RSI'] < 30, 'Oversold', 
                                        np.where(grouped_df['RSI'] > 70, 'Overbought', 'Neutral')
                                        ) 
    #Let
    rsi_buy_threshold = 30 
    rsi_sell_threshold = 70 
    adx_trend_threshold = 25

    #Bring in ADX data to measure trend strength 
    grouped_df['+DI'] = ta.PLUS_DI(grouped_df['High'], grouped_df['Low'], grouped_df['Close'], timeperiod=14)
    grouped_df['-DI'] = ta.MINUS_DI(grouped_df['High'], grouped_df['Low'], grouped_df['Close'], timeperiod=14)
    grouped_df['ADX'] = ta.ADX(grouped_df['High'], grouped_df['Low'], grouped_df['Close'], timeperiod=14)

    #Create buy and sell signals based on strategy logic
    grouped_df['Buy Signal'] = (grouped_df['MA20'] > grouped_df['MA50']) & (grouped_df['RSI'] < rsi_buy_threshold) & (grouped_df['ADX'] > adx_trend_threshold)
    grouped_df['Sell Signal'] = (grouped_df['MA20'] < grouped_df['MA50']) & (grouped_df['RSI'] > rsi_sell_threshold) & (grouped_df['ADX'] > adx_trend_threshold)
    
    return grouped_df

def calculate_metrics(grouped_df, risk_free_rate_annual=0.04, trading_days=252): 
    prices = grouped_df['Close']
    returns = prices.pct_change().dropna() 
    #Let 
    risk_free_rate_daily = risk_free_rate_annual/trading_days

    excess_returns = returns - risk_free_rate_daily
    avg_excess_returns = excess_returns.mean() 
    std_excess_returns = excess_returns.std() 
    sharpe_ratio_annualised = (avg_excess_returns / std_excess_returns) * np.sqrt(252)

    cumulative_returns = (1 + returns).cumprod() - 1
    total_returns = cumulative_returns.iloc[-1] * 100

    cumulative_growth = (1 + returns).cumprod()
    cumulative_max = cumulative_growth.cummax() 
    drawdown = (cumulative_growth - cumulative_max) / cumulative_max
    max_drawdown = drawdown.min() * 100 

    return sharpe_ratio_annualised, max_drawdown, total_returns


# Create main Streamlit app page
#******************************************************************************************************************************************************************************
def main(): 
    #Sidebar info 
    st.sidebar.title('Navigation')
    tickers_list = get_sp500_symbols()
    ticker = st.sidebar.selectbox('Select Stock Ticker:', tickers_list, index=0)   
    dt_col = st.sidebar.columns(2)
    end_date = dt_col[1].date_input('End Date', pd.to_datetime('today'))
    start_date = dt_col[0].date_input('Start Date', end_date - pd.DateOffset(years=1))
    rsi_graph = st.sidebar.checkbox('RSI Graph')
    adx_graph = st.sidebar.checkbox('ADX Graph')
    MA_graph = st.sidebar.checkbox('MA Graph')
    
    #Bring in and combine data
    df = get_data(ticker, start_date, end_date)
    sp500 = get_sp500_table()
    combined_df = pd.merge(df, sp500[['Symbol', 'Security', 'GICS Sector']], left_on='Ticker', right_on='Symbol')
    new_df = pd.DataFrame(combined_df).rename(columns={'GICS Sector': 'Sector'})


    col1, col2 = st.columns([3,1])
    with col1: 
        st.subheader(new_df['Security'][0])
    with col2: 
        st.subheader(new_df['Sector'][0])

    st.divider()


#Add Visualations
#******************************************************************************************************************************************************************************
    fig1 = go.Figure(data=[go.Candlestick(
        x=df['Date'], 
        open=df['Open'],
        high=df['High'], 
        low=df['Low'], 
        close=df['Close'], 
        increasing_line_color='#ff9900',
        decreasing_line_color="#efefef", 
        showlegend=False
    )])
    fig1.add_trace(go.Scatter(
        name='Buy Signal',        
        x=df['Date'][df['Buy Signal']], 
        y=df['Close'][df['Buy Signal']], 
        mode='markers', 
        marker=dict(symbol='arrow-up', color='green', size=12)
    ))
    fig1.add_trace(go.Scatter(
        name='Sell Signal', 
        x=df['Date'][df['Sell Signal']], 
        y=df['Close'][df['Sell Signal']], 
        mode='markers', 
        marker=dict(symbol='arrow-down', color='red', size=12)        
    ))
    fig1.update_layout(
        title=f'{ticker} Close Price Timeseries with Buy/Sell Signal 📈',
        xaxis_rangeslider_visible=False,
        legend=dict(orientation='h', x=1, y=1.2), #Required due to size of markers on legend
        yaxis_title='Close Price')

    st.plotly_chart(fig1)

    st.subheader('Strategy', divider='gray')
    col3, col4 = st.columns([1, 1])
    with col3: 
        st.markdown(
        '''
        Buy Signal:   
        - 20 day moving average > 50 day moving average 
        - RSI value < than our RSI buy threshold of 30
        - ADX trend strength indicator > our threshold of 25
        '''
        )

    with col4: 
        st.markdown(
        '''
        Sell Signal:   
        - 20 day moving average < 50 day moving average 
        - RSI value > than our RSI buy threshold of 70
        - ADX trend strength indicator > our threshold of 25
        '''
        )
    
    #Summary metrics
    st.subheader('Key Metrics', divider='gray')
    sharpe, drawdown, total_returns = calculate_metrics(df)
    mcol1, mcol2, mcol3, mcol4 = st.columns([1, 1, 1, 5])
    with mcol1: 
        st.metric('Sharpe Ratio', f'{sharpe:.2f}')
    with mcol2: 
        st.metric('Max Drawdown', f'{drawdown:.2f}%')
    with mcol3: 
        st.metric('Total Returns', f'{total_returns:+.2f}%')


    if sharpe < 1: 
        st.write('Returns are not compensating for the risk taken for this period')
    elif 1 <= sharpe < 2: 
        st.write('A decent risk-adjusted performance over this timescale')
    elif 2 <= sharpe < 3: 
        st.write('Indicates a strong risk adjusted return for this time frame')
    else:
        st.write('Over this period the investment has genererated excellent returns for the amount of risk taken') 
    
    if drawdown > -10: 
        st.write('Low drawdown, stock rarely suffers big losses') 
    elif -25 <= drawdown < -10: 
        st.write('Moderate drawdown, normal for most equities')
    elif -50 <= drawdown < -25: 
        st.write('High max drawdown - higher risk')
    else: 
        st.write('Very high max drawdown - a 50% loss requires a 100% gain to break even!')

    if rsi_graph:
        fig2 = go.Figure(data=go.Scatter(
            x=df['Date'], 
            y=df['RSI'],
            line=dict(color='#ff9900', width=2), 
            showlegend=False
        ))
        #Add overbought/oversold lines to graph 
        fig2.add_hline(y=30, line_color="#A8AAAD", line_width=2, line_dash='dot')
        fig2.add_hline(y=70, line_color="#A8AAAD", line_width=2, line_dash='dot')

        fig2.update_layout(
            title=f'{ticker} RSI Screen Indicator', 
            xaxis_title='Date', 
            yaxis_title='RSI',
            yaxis_range=[0, 100]
            )
        st.plotly_chart(fig2)    
    

    #ADX plots 
    if adx_graph:
        fig = make_subplots(rows=1, cols=1) 
        
        fig.add_trace(go.Scatter(name='+DI', x=df['Date'], y=df['+DI'], showlegend=True, legendgroup='2'), 
                    row=1, col=1)    
        fig.add_trace(go.Scatter(name='-DI', x=df['Date'], y=df['-DI'], showlegend=True, legendgroup='3'), 
                    row=1, col=1)
        fig.add_trace(go.Scatter(name='ADX', x=df['Date'], y=df['ADX'], showlegend=True, legendgroup='1'), 
                    row=1, col=1)

        fig.add_hline(y=25, line_width=2, line_dash='dash', line_color='grey')
        fig.update_layout(height=500, width=600, 
                        title=f'{ticker} ADX 14')
        st.plotly_chart(fig)


    #Plot Moving averages 
    if MA_graph:
        fig3 = go.Figure(data=go.Scatter(
            name=f'{ticker} Close Price',
            x=df['Date'], 
            y=df['Close'],
            line=dict(color='#ff9900', width=2), 
            showlegend=True
        ))
        fig3.add_scatter(
            name=f'{ticker} 20 Day MA', 
            x=df['Date'], 
            y=df['MA20'],  
            line=dict(color="#2f00ff", width=2, dash='dash'), 
            showlegend=True      
        )
        fig3.add_scatter(
            name=f'{ticker} 50 Day MA',       
            x=df['Date'], 
            y=df['MA50'],  
            line=dict(color="#058a38", width=2, dash='dash'), 
            showlegend=True      
        )

        fig3.update_layout(
        title=f'{ticker} Price and Moving Average', 
        #plot_bgcolor="#111010",
        xaxis_title='Date'
        ) 
        st.plotly_chart(fig3)  


main() 
