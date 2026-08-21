# System Architecture

## Purpose

The system produces store-level / basket-level cross-sell engine from retail transactions. It currently contains exploratory and batch Python implementations; the target production design separates extraction from the SQL Server warehouse, transformation and association mining, offline evaluation, and persistence and serving using PostgreSQL.

## Technology stack

The production stack favors a small, reproducible Python data application with explicit boundaries between warehouse extraction, basket transformation, association mining, evaluation, persistence, and orchestration. SQL Server remains read-only; PostgreSQL owns application state and published recommendation data.

| Area                                  | Current / target technology  |
| ------------------------------------- | -------------------------------------------------------------------- |
| Runtime                               | **Python 3.14.6**, pinned through `.python-version` and constrained by `pyproject.toml`|
| Dependency and environment management | **uv** with `pyproject.toml` and committed `uv.lock` for reproducible dependency resolution and environment synchronization |
| Data processing                       | **pandas** and **NumPy** for extraction results, validation, transformation, basket preparation, rule processing, and offline evaluation |
| Basket encoding                       | `mlxtend.preprocessing.TransactionEncoder` with sparse Boolean representations where appropriate |
| Association mining                    | **`mlxtend.frequent_patterns.fpgrowth`** for frequent-itemset mining and **`mlxtend.frequent_patterns.association_rules`** for rule generation and scoring; Apriori remains useful as an exploratory/baseline algorithm, while `fpgrowth_py` is to be retired from the production path |
| Rule quality                          | Python/pandas rule filtering using support ratio, absolute support count, confidence, lift, leverage, and explicit business-eligibility rules |
| Offline evaluation                    | Python with pandas/NumPy using temporal holdout evaluation; initial metrics include HitRate@K, Precision@K, Recall@K, catalog coverage, and store coverage |
| Source warehouse                      | **Microsoft SQL Server**, accessed read-only through **SQLAlchemy 2.x**, `pyodbc`, and Microsoft ODBC Driver for SQL Server; extraction queries are parameterized and source credentials are least-privilege   |
| Application database                  | **PostgreSQL** for model-ready baskets, published association rules, offline-evaluation results, pipeline-run metadata, and operational state |
| PostgreSQL access                     | **SQLAlchemy 2.x** with **psycopg 3** as the PostgreSQL DBAPI driver |
| Database migrations                   | **Alembic** for versioned and reversible PostgreSQL schema migrations |
| Configuration                         | Environment-backed application configuration with one documented `SOURCE_MSSQL_*`, `TARGET_POSTGRES_*`, and mining/evaluation parameter contract; secrets remain outside version control  |
| Scheduling                            | **External batch orchestration**; the application exposes deterministic, finite batch commands rather than embedding long-running scheduling loops |
| Observability                         | Structured application logging plus PostgreSQL pipeline-run metadata capturing execution status, source period, parameters, row/basket/rule counts, timings, code version, validation results, and failure reasons |
| Exploration                           | **Jupyter notebooks** for experiments and analysis; notebooks use repository-relative paths and synthetic or explicitly approved reference datasets rather than committed raw production transactions |
| Testing                               | **pytest** and **pytest-cov** for unit, regression, data-quality, and integration tests; ordinary unit tests remain independent of SQL Server, PostgreSQL, Spark, Java, and live ODBC connectivity |
| Static analysis                       | **Ruff** for Python linting and, when adopted across the application package, formatting and enforceable code-quality rules |
| Integration testing                   | GitHub Actions with disposable PostgreSQL for migration and persistence tests; SQL Server behavior is tested primarily through interfaces, fixtures, and contract tests rather than CI access to the production warehouse |
| Development harness                   | **uv**, pytest, pytest-cov, Ruff, repository/notebook validators, `AGENTS.md` guidance, deterministic fixtures, and **GitHub Actions** |
| Scale-out processing                  | **PySpark is optional and deferred**; introduce it only if representative benchmarks show the pandas/FP-Growth batch path cannot meet required runtime or memory targets |


## Business flow

1. Sales transactions are recorded in the enterprise warehouse.
2. The pipeline selects a completed reporting period and extracts store, bill, item, product, quantity, and sales attributes.
3. It removes excluded products and converts transactions into baskets by store and bill.
4. FP-Growth or Apriori identifies frequent itemsets; association rules are calculated and scored with support, confidence, lift, and related metrics.
5. Approved results are stored in PostgreSQL for downstream recommendation experiences and reporting.
6. A run is observable, validated, and promoted only after data-quality and model/business checks pass.

## Data flow

This is the future architecture for the store-level / basket-level cross-sell engine. It is designed to be modular, testable, and observable. The SQL Server warehouse is read-only; all application writes are to PostgreSQL.

```mermaid
flowchart TD

    SOURCE["SQL Server Warehouse — READ ONLY<br/>FactSalesTrxNew + DimDate + DimItem"]

    subgraph L1["1. Extraction & Transformation Layer"]
        direction TD

        EXT["Extract Source Period"]
        VAL["Validate Source Data<br/>schema · freshness · completeness · grain · nulls"]
        CLEAN["Cleanse & Normalize<br/>valid sales · positive quantity · eligible SKU"]
        DEDUP["Deduplicate"]
        BASKET["Build Canonical Store Baskets<br/>Store + Transaction → Item Set"]

        EXT --> VAL --> CLEAN --> DEDUP --> BASKET
    end

    subgraph L2["2. Association Mining Layer"]
        direction TD

        ENCODE["Encode Baskets<br/>Sparse Boolean Transaction Matrix"]
        FPG["Frequent Itemset Mining<br/>FP-Growth"]
        RULES["Association Rule Generation<br/>support · confidence · lift · leverage"]
        STAT["Statistical Rule Filters<br/>support ratio · support count · confidence · lift"]
        BUSINESS["Business Eligibility Filters<br/>active SKU · assortment · exclusions"]

        ENCODE --> FPG --> RULES --> STAT --> BUSINESS
    end

    subgraph L3["3. Offline Evaluation Layer"]
        direction TD

        HOLDOUT["Temporal Holdout Baskets"]
        SIM["Simulate Cross-Sell Recommendations"]
        METRICS["Evaluate<br/>HitRate@K · Precision@K · Recall@K · Coverage"]
        GATE{"Meets Publication Guardrails?"}

        HOLDOUT --> SIM
        SIM --> METRICS --> GATE
    end

    subgraph L4["4. Persistence & Serving Layer"]
        direction TD

        PG["PostgreSQL"]

        RUN["Pipeline Run Metadata"]
        BASKETDB["Model-Ready Baskets"]
        RULEDB["Published Recommendation Rules"]
        EVALDB["Evaluation Results"]

        RETRIEVE["Cross-Sell Candidate Retrieval"]
        RUNTIME["Runtime Business Filters"]
        RANK["Candidate Ranking"]
        TOPN["Top-N Cross-Sell Items"]

        CONSUMERS["Recommendation Consumers"]
        ANALYTICS["Analytics"]
        MONITOR["Operational Monitoring"]

        PG --> RUN
        PG --> BASKETDB
        PG --> RULEDB
        PG --> EVALDB

        RULEDB --> RETRIEVE --> RUNTIME --> RANK --> TOPN --> CONSUMERS

        RULEDB --> ANALYTICS
        EVALDB --> ANALYTICS
        RUN --> MONITOR
    end

    SOURCE --> EXT
    BASKET --> ENCODE

    BUSINESS --> SIM

    GATE -- "Pass" --> PG
    GATE -- "Fail" --> REJECT["Reject Candidate Model / Rule Set"]

    BASKET --> BASKETDB
```

### Extraction/Transformation Layer

This layer converts warehouse sales rows into the canonical input contract for the model.

```mermaid
flowchart TD

    MSSQL["SQL Server DBWH_8555<br/>READ ONLY"]

    QUERY["Parameterized Extraction Query<br/>Source Period + Required Columns"]

    RAW["Raw Extracted Sales Lines"]

    SCHEMA{"Schema Valid?"}
    PERIOD{"Period Complete?"}
    GRAIN{"Transaction Grain Valid?"}

    SALE["Sales-Line Eligibility"]
    QTY{"POS_FINAL_QTY > 0?"}
    SKU{"Recommendation-Eligible SKU?"}
    VOID{"Return / Void / Cancellation?"}

    DEDUP["Deduplicate Sales Lines"]

    TXKEY["Construct Canonical Transaction Key<br/>Store + Business Date + Bill / POS key"]

    GROUP["Group by Transaction Key"]

    BASKET["Canonical Basket<br/>store_code<br/>transaction_key<br/>business_date<br/>item_codes[]"]

    REJECT["Reject / Quarantine<br/>with reason"]

    MSSQL --> QUERY --> RAW

    RAW --> SCHEMA
    SCHEMA -- No --> REJECT
    SCHEMA -- Yes --> PERIOD

    PERIOD -- No --> REJECT
    PERIOD -- Yes --> GRAIN

    GRAIN -- No --> REJECT
    GRAIN -- Yes --> SALE

    SALE --> QTY
    QTY -- No --> REJECT
    QTY -- Yes --> SKU

    SKU -- No --> REJECT
    SKU -- Yes --> VOID

    VOID -- Yes --> REJECT
    VOID -- No --> DEDUP

    DEDUP --> TXKEY --> GROUP --> BASKET
```

**Responsibility**
This layer should answer:

> What exactly constitutes one valid Pepito retail basket?

That definition should be settled here—not inside FP-Growth.

### Association Mining Layer

This layer receives already-valid baskets. It should contain no SQL Server logic and ideally no persistence logic.

```mermaid
flowchart TD

    BASKETS["Canonical Store Baskets"]

    STORE["Partition / Group by Store"]

    ENCODE["TransactionEncoder<br/>Sparse Boolean Representation"]

    FPG["FP-Growth<br/>min_support"]

    ITEMSETS["Frequent Itemsets<br/>itemsets + support"]

    RULE["association_rules()"]

    SCORED["Scored Candidate Rules<br/>antecedent<br/>consequent<br/>support<br/>confidence<br/>lift<br/>leverage"]

    COUNT["Calculate Absolute Support Count"]

    STAT{"Statistical Guardrails Passed?"}

    ELIGIBLE{"Business Eligibility Passed?"}

    CANDIDATE["Candidate Cross-Sell Rule"]

    DROP["Discard Rule<br/>record reason / statistics"]

    BASKETS --> STORE --> ENCODE --> FPG --> ITEMSETS --> RULE --> SCORED

    SCORED --> COUNT --> STAT

    STAT -- No --> DROP
    STAT -- Yes --> ELIGIBLE

    ELIGIBLE -- No --> DROP
    ELIGIBLE -- Yes --> CANDIDATE
```

`mlxtend.fpgrowth()` supports Boolean/0–1 encoded transaction DataFrames and sparse DataFrames, and returns `support` plus `itemsets`, which makes it a clean fit for this boundary.

**Important separation**

Keep:
```
statistical filtering
```

separate from:

```
business filtering
```

For example:

**Statistical:**

```
support >= 0.001
support_count >= N
confidence >= X
lift >= Y
```

**Business:**

```
consequent is active
consequent is sellable
consequent is recommendation eligible
valid for store assortment
not a service SKU
not a shopping bag
```

That separation will make later tuning much cleaner.

### Offline Evaluation Layer

This layer answers a different question from association-rule mining:

> Do the rules actually work as cross-sell recommendations on unseen future baskets?

```mermaid
flowchart TD

    HIST["Historical Canonical Baskets"]

    SPLIT["Temporal Split"]

    TRAIN["Training Window"]
    TEST["Future Holdout Window"]

    MINE["Generate Candidate Rules<br/>from Training Window"]

    TESTBASKET["Select Holdout Basket"]

    MASK["Mask / Hide Target Item"]

    INPUT["Observed Basket Items"]

    MATCH["Find Rules Where<br/>Antecedent ⊆ Observed Basket"]

    EXCLUDE["Remove Items Already in Basket"]

    FILTER["Apply Store / SKU Eligibility"]

    RANK["Rank Candidates"]

    TOPK["Top-K Recommendations"]

    COMPARE["Compare Against Hidden Item"]

    METRICS["Aggregate Metrics<br/>HitRate@K<br/>Precision@K<br/>Recall@K<br/>Coverage"]

    GUARD{"Meets Model Guardrails?"}

    APPROVE["Approve Rule Set"]
    REJECT["Reject / Investigate"]

    HIST --> SPLIT

    SPLIT --> TRAIN
    SPLIT --> TEST

    TRAIN --> MINE

    TEST --> TESTBASKET --> MASK
    MASK --> INPUT

    MINE --> MATCH
    INPUT --> MATCH

    MATCH --> EXCLUDE --> FILTER --> RANK --> TOPK --> COMPARE
    MASK --> COMPARE

    COMPARE --> METRICS --> GUARD

    GUARD -- Yes --> APPROVE
    GUARD -- No --> REJECT
```

This separation is important because rule metrics and recommendation metrics are not interchangeable. `association_rules()` measures rule characteristics such as support, confidence, lift, leverage and conviction.

Offline evaluation then assesses the behavior of the whole recommendation procedure against future baskets.


### Persistence & Serving Layer

This is where PostgreSQL becomes an application database, rather than another warehouse.

```mermaid
flowchart TD

    APPROVED["Approved Cross-Sell Model Run"]

    PG["PostgreSQL"]

    RUN["recommendation_run<br/>run metadata + parameters"]

    BASKET["basket / basket_item<br/>model-ready baskets"]

    RULE["recommendation_rule<br/>published rules"]

    EVAL["evaluation_run<br/>offline metrics"]

    REQUEST["Recommendation Request<br/>Store + Current Basket"]

    LOOKUP["Retrieve Matching Rules"]

    MATCH["Antecedent Matches Basket?"]

    REMOVE["Remove Already-Purchased Items"]

    ASSORT["Store Assortment / Eligibility"]

    RANK["Rank Candidate Consequents"]

    TOPN["Return Top-N ItemCodes"]

    POS["POS / Retail Application"]
    BI["Analytics"]
    OPS["Operational Monitoring"]

    APPROVED --> PG

    PG --> RUN
    PG --> BASKET
    PG --> RULE
    PG --> EVAL

    REQUEST --> LOOKUP
    RULE --> LOOKUP

    LOOKUP --> MATCH --> REMOVE --> ASSORT --> RANK --> TOPN

    TOPN --> POS

    RULE --> BI
    EVAL --> BI

    RUN --> OPS
```

It would keep the designed normalized basket + basket_item rather than copying all warehouse sales-line fields into PostgreSQL. PostgreSQL can support structured alternatives such as arrays or jsonb, but normalization remains a clearer primary contract for this relational workflow; PostgreSQL's documentation confirms native jsonb support and associated indexing/query facilities if you later need a derived structured representation.

### Relationships between layers

The most useful architectural rule is that every layer has a **defined input and output contract**:

```mermaid
flowchart LR

    L1["Extraction & Transformation"]

    C1["Canonical Basket Contract"]

    L2["Association Mining"]

    C2["Candidate Rule Contract"]

    L3["Offline Evaluation"]

    C3["Approved Rule Set<br/>+ Evaluation Contract"]

    L4["Persistence & Serving"]

    L1 --> C1 --> L2 --> C2 --> L3 --> C3 --> L4
```

## Current repository components

- `apriori_store.py`: per-store FP-Growth batch implementation and existing SQL Server persistence code that must be migrated to PostgreSQL.
- `apriori.py`: earlier all-store Apriori implementation.
- `notebooks/`: exploratory analysis and algorithm experiments.
- `datasets/`: local reference or exploratory datasets; production data must not be added without an approved data-governance exception.
- `executable/`: batch launchers.
- `logs/`: local runtime logs, excluded from version control.

## Development harness flow

```text
Issue branch and local change
           |
           v
uv locked environment -> repository checks -> notebook checks -> scoped Ruff -> pytest
           |
           v
GitHub Actions: blocking Windows harness + advisory Linux portability
           |
           v
Reviewed pull request to develop -> staging -> main
```

Harness tests use repository fixtures and notebook JSON only. They do not connect to SQL Server or PostgreSQL and do not execute Spark.

## Architectural rules

- SQL Server is a source only; PostgreSQL owns all application writes.
- Data access, transformation, mining, and persistence must have explicit interfaces and independently testable behavior.
- Run metadata must identify source period, code version, parameters, row counts, outputs, status, and error reason.
- Schema changes are versioned, reviewed, and reversible.
