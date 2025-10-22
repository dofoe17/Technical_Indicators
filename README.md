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

