Bring in S&P data by web scraping data from Wikipedia using BeautifulSoup. 
```ruby
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
```

We then calculate our technical indicators. 20 and 50 moving averages, RSI and ADX indicator. Once calculated we can then add signal columns to our dataframe: 
```ruby
    grouped_df['Buy Signal'] = (grouped_df['MA20'] > grouped_df['MA50']) & (grouped_df['RSI'] < rsi_buy_threshold) & (grouped_df['ADX'] > adx_trend_threshold)
    grouped_df['Sell Signal'] = (grouped_df['MA20'] < grouped_df['MA50']) & (grouped_df['RSI'] > rsi_sell_threshold) & (grouped_df['ADX'] > adx_trend_threshold)
```


Below shows the main page of the app: 

<img width="1915" height="787" alt="image" src="https://github.com/user-attachments/assets/ca735abf-dd9a-4381-b725-d868659886dc" />

Heading over to the navigation page, we can search using the drop down to select the ticker of any S&P 500 company, amend the date of the data on the main page and add the graphs of our indicators. 

<img width="1857" height="845" alt="image" src="https://github.com/user-attachments/assets/e537d91a-6ed2-45c8-87b0-afad922bf226" />


Finally added key metric data and conditional summary: 

<img width="968" height="256" alt="image" src="https://github.com/user-attachments/assets/ae88cddf-37ca-407f-a8e0-f69e18b7009c" />



