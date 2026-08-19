import pandas as pd
import numpy as np
import os
import schedule
import time
import calendar
import datetime as dt
import logging
import sys
from datetime import datetime, timedelta
from mlxtend.frequent_patterns import apriori
from mlxtend.frequent_patterns import association_rules
from sqlalchemy import create_engine, text




def setup_monthly_logging(base_log_filename):

    logger.setLevel(logging.INFO) # Set the logging level (e.g., INFO, DEBUG, WARNING, ERROR)

    # Define the log message formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Ensure the 'logs' directory exists
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Generate the log filename with the current year and month
    current_month_str = datetime.now().strftime("%Y-%m") # Example: '2025-05'
    # Split the base filename to insert the month string before the extension
    name_without_ext, ext = os.path.splitext(base_log_filename)
    log_filename_with_month = f"{name_without_ext}.{current_month_str}{ext}"
    full_log_path = os.path.join(log_dir, log_filename_with_month)

    # Create a FileHandler. Use 'a' mode to append if the file already exists,
    # or create it if it doesn't (which will happen on the first run of a new month).
    file_handler = logging.FileHandler(full_log_path, mode='a')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    # Optionally, add a StreamHandler to see logs in the console during execution
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

logger = logging.getLogger(__name__)

db_user = os.environ.get('dbwh_8555_user')
db_pass = os.environ.get('dbwh_8555_pass')

connection_string = f"mssql+pyodbc://{db_user}:{db_pass}@192.168.85.55/DBWH_8555?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(connection_string)

def get_data(month, year):

    last_day = calendar.monthrange(year, month)[1]  

    start_date = f'{year}-{month:02d}-01'
    end_date = f'{year}-{month:02d}-{last_day:02d}'

    query = text(
    """
    SELECT 
        dd.[date] AS TRX_date,
        [StoreCode],
        [BillNo],
        [ItemCode],
        ITEMLONGNAME,
        [Quantity],
        DEPARTMENT,
        CLASS,
        SUBCLASS,
        [UOM_CD],
        [TotalAmt],
        [NetValue],
        [WACValue],
        [CSM_QTY],
        [CONSIGN_FINAL_QTY],
        [POS_FINAL_QTY]
    FROM [DBWH_8555].[dbo].[FactSalesTrxNew] fstn
    INNER JOIN dimdate dd ON dd.datekey = fstn.DateKey
    INNER JOIN DimItem di ON fstn.ItemCode = di.ITMCD
    WHERE dd.[date] BETWEEN :start_date AND :end_date
    """)

    logger.info(f"Getting data from {start_date} to {end_date}")

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'start_date': start_date, 'end_date': end_date})

            num_of_row = len(df)
            logger.info(f'{num_of_row} of rows will be processed')

    except Exception as e:
        logger.error(f'Getting Data Error: {str(e)}')





    # Data Cleaning
    df = df[~df['ITEMLONGNAME'].str.contains('PEPITO BAG M|PEPITO BAG L', case=False, na=False)]

    return df

def process_apriori(date_month, date_year):

    df = get_data(date_month, date_year)

    logger.info(f"Processing Apriori... :)")
    

    product_frequency = df.groupby('ITEMLONGNAME').size().sort_values(ascending=False)
    top_products = product_frequency.head(10).index  # Focus on top 10 products

    df_filtered = df[df['ITEMLONGNAME'].isin(top_products)]

    # Create transaction matrix
    transactions = df_filtered.groupby(['BillNo', 'ITEMLONGNAME'])['POS_FINAL_QTY'].sum().unstack(fill_value=0)
    transactions = transactions.apply(pd.to_numeric, errors='coerce').fillna(0)

    transactions_binary = transactions.gt(0) # convert the col value to bool type

    # Generate frequent itemsets with very low min_support to see more combinations
    frequent_itemsets = apriori(
        transactions_binary, 
        min_support=0.001,  # Very low threshold to see more combinations #PARAMETER TUNING
        use_colnames=True)
    
    rules = association_rules(frequent_itemsets, 
                         metric="lift",
                         min_threshold=1.0) #PARAMETER TUNING
    
    num_of_rules = len(rules)
    logger.info(f"{num_of_rules} rows of Apriori rules genereted")

    # Sort rules by lift
    rules = rules.sort_values('lift', ascending=False)
    rules['month_year'] = f'{int(date_month):02d}-{date_year}'
    #rules.to_csv('product_associations.csv', index=False)

    return rules

def write_to_db(rules):

    #rules['antecedents'] = rules['antecedents'].str.replace("frozenset\\(|[\\{\\}']|\\)", "", regex=True)
    #rules['consequents'] = rules['consequents'].str.replace("frozenset\\(|[\\{\\}']|\\)", "", regex=True)

    rules['antecedents'] = rules['antecedents'].apply (lambda x: ', '.join(list(x)))
    rules['consequents'] = rules['consequents'].apply (lambda x: ', '.join(list(x)))
    #rules['conviction'] = rules['conviction'].replace([np.inf, -np.inf], 999999.0)
    rules['conviction'] = rules['conviction'].astype(str)

    #cols_to_drop = ['representativity', 'jaccard', 'certainty', 'kulczynski'] # add new metrics at mlxtend 0.23.x and up
    #rules = rules.drop(columns=cols_to_drop, errors='ignore')

    #rules.head(3)
    #rules.info()

    logger.info(f"Writing rules to DB...")
    try:
        rules.to_sql('FactProductAssociations', con=engine, if_exists='append', chunksize=10000, index=False)
        logger.info(f"Writing rules to DB Completed")

    except Exception as e:
        logger.error(f'Writing rules to DB error: {str(e)}')

def load_latest_date():
    query = text(
    """
    SELECT TOP 1 month_year 
        FROM FactProductAssociations 
        ORDER BY 
            CAST(SUBSTRING(month_year, 4, 4) AS INT) DESC, 
            CAST(SUBSTRING(month_year, 1, 2) AS INT) DESC
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        start_month, start_year = 1, 2025
        logger.info(f"No data found, starting from {start_month:02d}-{start_year}")
        return start_month, start_year
        
    month_year = df['month_year'].iloc[0] 
    month, year = month_year.split('-') 
    month = int(month)
    year = int(year)

    logger.info(f"Latest data from DB: {month:02d}-{year}")

    # Increment month and adjust year if needed
    if month == 12:
        month = 1
        year += 1
    else:
        month += 1

    logger.info(f"Next month to process: {month:02d}-{year}")
    return month, year

def main():
    logger = setup_monthly_logging(base_log_filename="apriori.log")

    try:
        logger.info("Application is starting...")

        while True: ## main APP start from here
            today = dt.date.today()
            
            today_month = int(today.strftime('%m'))  # e.g., "05"
            today_year = int(today.strftime('%Y'))   # e.g., "2025"

            last_month_str, last_year_str = load_latest_date()

            last_month = int(last_month_str)
            last_year = int(last_year_str)

            if last_month == today_month and last_year == today_year:
                logger.info(f"Data has been processed from the latest month available")
                logger.info(f"Exiting...")
                #print("Both start and end dates have reached yesterday's date. Exiting the loop.")
                break  # Exit the loop

            logger.info(f"Processing data for {last_month:02d}-{last_year}")
        
            new_rules = process_apriori(last_month, last_year)
            #write_to_db(new_rules)
        

    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
    finally:
        logger.info("Application is shutting down.")
        # It's good practice to explicitly close handlers, especially for short-lived apps
        # to ensure all logs are flushed before exit.
        for handler in logger.handlers[:]: # Iterate over a copy of the list
            handler.close()
            logger.removeHandler(handler)
    '''
    while True:
        today = dt.date.today()
        

        today_month = int(today.strftime('%m'))  # e.g., "05"
        today_year = int(today.strftime('%Y'))   # e.g., "2025"

        last_month_str, last_year_str = load_latest_date()

        last_month = int(last_month_str)
        last_year = int(last_year_str)

        if last_month == today_month and last_year == today_year:
            logger.info(f"Data has been processed from the latest month available")
            logger.info(f"Exiting...")
            #print("Both start and end dates have reached yesterday's date. Exiting the loop.")
            break  # Exit the loop

        logger.info(f"Processing data for {last_month:02d}-{last_year}")
    
        new_rules = process_apriori(last_month, last_year)
        write_to_db(new_rules)    

    sys.exit()
    '''
 

if __name__ == "__main__":
    main()