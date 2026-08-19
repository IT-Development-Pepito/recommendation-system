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
from mlxtend.frequent_patterns import association_rules
from sqlalchemy import create_engine, text
from mlxtend.preprocessing import TransactionEncoder
from fpgrowth_py import fpgrowth
from itertools import combinations






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

def get_data(month, year='2025'): #set default value to 2025

    last_day = calendar.monthrange(year, month)[1]  # get last date at urrent month

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

    logger.info(f"Geting data from {start_date} to {end_date}")

    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'start_date': start_date, 'end_date': end_date})

            num_of_row = len(df)
            logger.info(f'{num_of_row} of rows will be processed')

    except Exception as e:
        logger.error(f'Getting Data Error: {str(e)}')


    # Data Cleaning
    df = df[~df['ITEMLONGNAME'].str.contains('pepito bag', case=False, na=False)]

    return df



def process_apriori(date_month, date_year):
    df = get_data(date_month, date_year)

    logger.info("Processing Apriori... :)")

    all_rules = []
    month_year = f'{int(date_month):02d}-{date_year}'

    item_code_to_item_name = dict(zip(df['ItemCode'], df['ITEMLONGNAME']))

    for store_code, store_df in df.groupby('StoreCode'):
        logger.info(f"Processing store: {store_code}")

        '''
        #1
        # Get top 10 most frequent products for this store
        product_frequency = store_df.groupby('ItemCode').size().sort_values(ascending=False)
        top_products = product_frequency.head(10).index

        store_df_filtered = store_df[store_df['ItemCode'].isin(top_products)]

        # Create transaction matrix
        transactions = store_df_filtered.groupby(['BillNo', 'ItemCode'])['POS_FINAL_QTY'] \
                                        .sum().unstack(fill_value=0)

        transactions = transactions.apply(pd.to_numeric, errors='coerce').fillna(0)
        transactions_binary = transactions.gt(0)  # Convert to boolean (True/False)
        
        '''
        '''
        #2
        transactions = store_df.groupby("BillNo")["ItemCode"].apply(list).tolist()

        te = TransactionEncoder()
        te_ary = te.fit(transactions).transform(transactions, sparse=True)

        transactions_binary = pd.DataFrame.sparse.from_spmatrix(
            te_ary,
            columns=te.columns_
        ).astype(pd.SparseDtype(bool, fill_value=False))

        # Generate frequent itemsets
        frequent_itemsets = fpgrowth(
            transactions_binary,
            min_support=0.001, # Only include itemsets appearing in ≥ 0.1% of transactions
            use_colnames=True,
            #max_len=2
        )
        # 1 store 4min
        '''
        #3
        transactions = (
            store_df.groupby("BillNo")["ItemCode"]
            .apply(lambda x: list(set(x)))  # remove duplicates
            .apply(list).tolist()
        )
        n_transactions = len(transactions)

        freqItemSet, rules_fpg = fpgrowth(transactions, minSupRatio=0.001, minConf=0.0)
        transactions_sets = [set(t) for t in transactions]  # convert once, reuse

        def calc_support(itemset): 
            return sum(1 for t in transactions_sets if itemset.issubset(t)) / n_transactions
        
        frequent_itemsets = pd.DataFrame([
            {"itemsets": frozenset(itemset), "support": calc_support(itemset)}
            for itemset in freqItemSet
        ])

        # Ensure column dtypes
        frequent_itemsets["itemsets"] = frequent_itemsets["itemsets"].apply(frozenset)
        frequent_itemsets.drop_duplicates(subset=["itemsets"], inplace=True)
        frequent_itemsets.reset_index(drop=True, inplace=True)

        # --- Ensure subsets (fix for missing singletons) ---
        existing = set(frequent_itemsets["itemsets"])
        new_rows = []

        for itemset in list(existing):
            if len(itemset) > 1:  # only expand if size >= 2
                for i in range(1, len(itemset)):
                    for subset in combinations(itemset, i):
                        subset_fs = frozenset(subset)
                        if subset_fs not in existing:
                            new_rows.append({
                                "itemsets": subset_fs,
                                "support": calc_support(subset_fs)
                            })
                            existing.add(subset_fs)

        if new_rows:
            frequent_itemsets = pd.concat(
                [frequent_itemsets, pd.DataFrame(new_rows)],
                ignore_index=True
            )
        # -- END --
        
        logger.info(f"Unique transactions (BillNo) for store {store_code}: {n_transactions}")
        if frequent_itemsets.empty:
            logger.info(f"No frequent itemsets found for store {store_code}")
            continue

        # Generate association rules
        rules = association_rules(
            frequent_itemsets, 
            metric="lift", 
            min_threshold=1.0 # lift, 1.0
        ) 

        if not rules.empty:

            # Unpack frozenset
            rules['antecedents'] = rules['antecedents'].apply(lambda x: ', '.join(sorted(x)))
            rules['consequents'] = rules['consequents'].apply(lambda x: ', '.join(sorted(x)))

            rules['antecedents_names'] = rules['antecedents'].apply(
                lambda x: ', '.join(item_code_to_item_name.get(code.strip(), code.strip()) for code in x.split(','))
            )
            rules['consequents_names'] = rules['consequents'].apply(
                lambda x: ', '.join(item_code_to_item_name.get(code.strip(), code.strip()) for code in x.split(','))
            )

            rules['store_code'] = store_code
            rules['month_year'] = month_year
            all_rules.append(rules)

        logger.info(f"{len(rules)} rules generated for store {store_code}")

    # Combine all rules
    if all_rules:
        combined_rules = pd.concat(all_rules, ignore_index=True)
        logger.info(f"{len(combined_rules)} total rules generated across all stores")
        # combined_rules.to_csv('product_associations.csv', index=False)
        return combined_rules
    else:
        logger.info("No rules generated for any store.")
        return pd.DataFrame()

def write_to_db(rules):

    #rules['antecedents'] = rules['antecedents'].str.replace("frozenset\\(|[\\{\\}']|\\)", "", regex=True)
    #rules['consequents'] = rules['consequents'].str.replace("frozenset\\(|[\\{\\}']|\\)", "", regex=True)

    #rules['antecedents'] = rules['antecedents'].apply (lambda x: ', '.join(list(x)))
    #rules['consequents'] = rules['consequents'].apply (lambda x: ', '.join(list(x)))
    #rules['conviction'] = rules['conviction'].replace([np.inf, -np.inf], 999999.0)

    # Reorder columns
    rules = rules [['antecedents', 'antecedents_names','consequents',
                'consequents_names', 'antecedent support',
                'consequent support', 'support', 'confidence', 'lift',
                'representativity', 'leverage', 'conviction', 'zhangs_metric',
                'jaccard', 'certainty', 'kulczynski', 'store_code', 'month_year']]
    
    rules['conviction'] = rules['conviction'].astype(str)

    #rules.head(3)
    #rules.info()

    logger.info(f"Writing rules to DB..")
    try:
        rules.to_sql('FactProductAssociationsStore', con=engine, if_exists='append', chunksize=10000, index=False)
        logger.info(f"Writing rules to DB Completed")

    except Exception as e:
        logger.error(f'Writing rules to DB error: {str(e)}')

def load_latest_date():
    query = text(
    """
    SELECT TOP 1 month_year 
        FROM FactProductAssociationsStore 
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

    except Exception as e:
        logger.exception(f"An unexpected error occurred during execution: {e}")
    finally:
        logger.info("Application is shutting down.")
        # to ensure all logs are flushed before exit.
        for handler in logger.handlers[:]: # Iterate over a copy of the list
            handler.close()
            logger.removeHandler(handler)
    
   

if __name__ == "__main__":
    main()