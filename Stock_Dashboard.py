import yfinance as yf
import pandas as pd
from datetime import datetime
import streamlit as st
import plotly.express as px


st.set_page_config(layout="wide")


#Set initial starting information 
df = pd.read_csv('/Users/karol/Documents/Wake Forest/Wake Wealth Initiative/Participant Allocations.csv')

start_date = "2024-12-09"  # Adjust the start date as needed
end_date = datetime.today().strftime('%Y-%m-%d')    # Adjust the end date as needed
stop_date = '2025-04-30'
initial_investment = 10000

if end_date >= stop_date:
    end_date = stop_date
else:
    end_date = end_date


num_participants = len(df['Name'].unique())
final = pd.DataFrame()

#Pull sector and industry information, add it to the df
# Function to get sector and industry for each ticker
crypto_tickers = ['BTC', 'ETH']
index_funds = ['SWPPX', 'FXAIX']

def get_sector_industry(ticker):
    if ticker in crypto_tickers:
        stock = yf.Ticker(ticker)
        long_name = stock.info.get('longName', 'N/A')
        return long_name, 'Crypto', 'Cryptocurrency'
    elif ticker in index_funds:
        stock = yf.Ticker(ticker)
        long_name = stock.info.get('longName', 'N/A')
        return long_name, 'Exchange-Traded Funds', 'Index Fund'
    else:
        stock = yf.Ticker(ticker)
        long_name = stock.info.get('longName', 'N/A')
        sector = stock.info.get('sector', 'N/A')
        industry = stock.info.get('industry', 'N/A')
        return long_name, sector, industry

# Apply the function to each row and create new columns
df[['Stock Name','Sector', 'Industry']] = df['Stock'].apply(lambda x: pd.Series(get_sector_industry(x)))

# Display the updated DataFrame
#print(df)

#Pull and seperate allocation data by participant
for i in range (num_participants):
    row_list = []
    for j in range (len(df)):
        if df['Name'].iloc[j] == df['Name'].unique()[i]:
            name = df['Name'].unique()[i]
            row_list.append(j)
            mini_df = pd.DataFrame({'Stock': df['Stock'].iloc[min(row_list):max(row_list)+1], 
                                    'Percentage': df['Percentage'].iloc[min(row_list):max(row_list)+1]})

    ticker_column = 'Stock'  # Column with the company ticker symbols
    allocation_column = 'Percentage'  # Column with the allocation percentages

    # Create the dictionary
    allocations = dict(zip(mini_df[ticker_column], mini_df[allocation_column]))

    tickers = list(allocations.keys())

    # Download historical prices for each ticker
    data = yf.download(tickers, start=start_date, end=end_date)['Close']

    # Calculate initial shares based on initial prices and allocations
    initial_prices = data.iloc[0]
    shares = {
        ticker: (initial_investment * allocation) / initial_prices[ticker]
        for ticker, allocation in allocations.items()}

    # Create a DataFrame to store daily portfolio values
    daily_values = pd.DataFrame(index=data.index, columns=['Portfolio Value'])

    # Calculate portfolio value for each day based on actual market prices
    for date in data.index:
        portfolio_value = sum(data.loc[date, ticker] * shares[ticker] for ticker in tickers)
        daily_values.loc[date, 'Portfolio Value'] = portfolio_value

    # Convert the index to just the date and reset it as a column
    daily_values.index = pd.to_datetime(daily_values.index).date  # Ensure only date part
    daily_values.reset_index(inplace=True)
    daily_values.rename(columns={'index': 'Date'}, inplace=True)

    final[name] =  daily_values['Portfolio Value']
    
final.insert(0, 'Date', daily_values['Date'])
#print(final) #New dataframe containing each portfolios position throughout designated period 

sp500 = final['S&P 500']

final = final.drop(columns=['S&P 500'])
df = df[df['Name'] != 'S&P 500']
num_participants = len(df['Name'].unique())
# Reshape your data from wide format to long format
long_df = final.melt(id_vars=["Date"], var_name="Person", value_name="Position Value")

# Save the reshaped data to a new CSV
#long_df.to_csv('reshaped_data.csv', index=False)

#Current Positions Ranked
last_row = final.iloc[-1, 1:]

ranked_table = last_row.sort_values(ascending=False).reset_index()
ranked_table.columns = ['Participant', 'Value']
ranked_table['Value'] = pd.to_numeric(ranked_table['Value'])
#ranked_table['Value'] = pd.to_numeric(ranked_table['Value']).round(0)

ranked_table.insert(0, 'Rank', range(1, len(ranked_table) + 1))

ranked_table['Change'] = (((ranked_table['Value'] - initial_investment) / initial_investment) * 100).round(2)
ranked_table['Change'] = pd.to_numeric(ranked_table['Change'], errors='coerce')
ranked_table['Value'] = ranked_table['Value'].apply(lambda x: f"${x:,.0f}")

ranked_table['Change'] = ranked_table['Change'].apply(lambda x: f"{x:.2f}%")

sp_change = ((( sp500.iloc[-1] - sp500.iloc[0])/sp500.iloc[0])*100).round(2)


#print(ranked_table)

#Find most picked stocks 
counted_per_stock = df['Stock'].value_counts()
counted_per_sector = df['Sector'].value_counts()
counted_per_industry = df['Industry'].value_counts()

#Find where a stock was selected more than once
filtered_per_stock = counted_per_stock[counted_per_stock > 1]

#Find count of unique stocks
stock_unique_count = df['Stock'].nunique()
sector_unique_count = df['Sector'].nunique()
industry_unique_count = df['Industry'].nunique()

#Format date and dollars
def format_date_with_suffix(date_input):
    # Check if input is a string and convert it to a date object
    if isinstance(date_input, str):
        date_object = datetime.strptime(date_input, '%Y-%m-%d')
    elif isinstance(date_input, (datetime, date)):
        date_object = date_input
    else:
        raise ValueError("Input must be a 'YYYY-MM-DD' string or a date/datetime object")
    
    # Extract the day to calculate the suffix
    day = date_object.day
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    
    # Format the date with the suffix
    formatted_date = date_object.strftime(f'%B {day}{suffix}, %Y')
    return formatted_date

formatted_investment = f"${initial_investment:,.0f}"


#Start streamlit dashbaord
col1, col2 = st.columns(2)
with col1:
    st.image("WF_Business.png", width=200)
with col2:
    st.subheader("Wake Wealth Initiative - Stock Simulation Dashboard")
   # st.write("Made by Karol Kusmierczuk")

tab1, tab2, tab3 = st.tabs(["Overall Group Performance", "Individual Performance", "About"])
    
with tab1:
    fig = px.line(long_df, x='Date', y='Position Value', color='Person', 
              labels={'Position Value': 'Value', 'Date': ''}, 
              title='Daily Positions for All Participants', hover_data=['Person'])
    fig.update_traces(
    hovertemplate="%{customdata[0]}<br>%{x}<br>$%{y:,.0f}<extra></extra>"  # Custom formatting
)
    st.plotly_chart(fig)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f'Below are the current rankings as of {format_date_with_suffix(end_date)}:')
        st.dataframe(ranked_table, hide_index=True, use_container_width=True)
        st.write(f'The same investment in just the S&P 500 would result in a value of ${(sp500.iloc[-1]):,.0f}, changing by {sp_change}%.')

    with col2:
        sector_count = df['Sector'].value_counts().reset_index()
        sector_count.columns = ['Sector', 'Count']
        fig = px.bar(sector_count, x='Sector', y='Count', title='Count of Sectors Invested In')
        fig.update_traces(textposition='outside')
        fig.update_layout(yaxis_title="")
        fig.update_traces(
    hovertemplate="%{x}<br>%{y}<extra></extra>"  # Custom formatting
)
        st.plotly_chart(fig)

   


    with tab2:
        selected_person = st.selectbox("Select a participant:", df['Name'].unique().tolist())


        rank_filter = ranked_table[ranked_table['Participant'] == selected_person]

        position = rank_filter['Rank'].iloc[0]
        value = rank_filter['Value'].iloc[0]
        grown = rank_filter['Change'].iloc[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f'Portfolio Position: {position}/{num_participants}')
        with col2:
            st.write(f'Portfolio Value: {value}')
        with col3:
            st.write(f'Portfolio Growth: {grown}')



        fig = px.line(final, x='Date', y=selected_person, 
              labels={'Position Value': 'Position Value', 'Date': 'Date'}, 
              title=f'''{selected_person}'s Daily Positions''')
        fig.add_hline(y=10000, line_dash="dash", line_color="red", annotation_text="Initial Investment", annotation_position="top right")
        fig.update_layout(yaxis_title="")
        fig.update_traces(
    hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>"  # Custom formatting
)
        st.plotly_chart(fig)


        filtered_df = df[df['Name'] == selected_person]
        col1, col2 = st.columns(2)
        with col1:
            st.write(f'{selected_person} invested in the following stocks:')
            stock_sector_df = filtered_df[['Stock', 'Stock Name', 'Sector', 'Industry']]
            st.dataframe(stock_sector_df, hide_index=True, use_container_width=True)
        with col2:
            filtered_sector_count = filtered_df.groupby('Sector').agg(Count=('Sector', 'size'), Total_Allocation=('Percentage', 'sum')).reset_index()
            fig = px.pie(filtered_sector_count, 
                values="Total_Allocation", 
                names="Sector", 
                title=f"{selected_person}'s Sectors",
                color_discrete_sequence=px.colors.qualitative.Set2,
                hover_data={'Count': True, 'Total_Allocation': True})  # Show count and allocation in hover tooltip

            # Customize hover info to show the count of sectors
            fig.update_traces(hovertemplate='<b>%{label}</b><br>' +  'Allocation: %{value:.2%}<br>')
            st.plotly_chart(fig)

    with tab3: #Overview
        st.write(f'This is a dashboard to track and compare stock portfolios for participants in the stock simulation held by the Wake Wealth Initiative.')
        st.write(f'The stocks were hypotetically bought on {format_date_with_suffix(start_date)} and the simulation will conclude on {format_date_with_suffix(stop_date)}.')      
        st.write(f'Each participant started with {formatted_investment} and was allowed to invest into a maximum of 10 stocks.')
        st.write(f'Dashboard created by Karol Kusmierczuk.')
