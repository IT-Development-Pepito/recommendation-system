# System Architecture

## Purpose

The system produces product-association recommendations from retail transactions. It currently contains exploratory and batch Python implementations; the target production design separates extraction from the SQL Server warehouse, transformation and recommendation generation, and persistence in PostgreSQL.

## Technology stack

| Area | Current / target technology |
| --- | --- |
| Runtime | Python |
| Data processing | pandas, NumPy |
| Association mining | `mlxtend` Apriori/rule generation and `fpgrowth_py` FP-Growth |
| Source warehouse | Microsoft SQL Server, accessed read-only through SQLAlchemy and an ODBC driver |
| Application database | PostgreSQL for ETL output, recommendation results, run metadata, and operational state |
| Scheduling / observability | Batch scheduler and structured application logs; to be formalized as the pipeline matures |
| Exploration | Jupyter notebooks and CSV reference datasets |
| Development harness | uv lockfile, pytest, Ruff, repository/notebook validators, GitHub Actions |

## Business flow

1. Sales transactions are recorded in the enterprise warehouse.
2. The pipeline selects a completed reporting period and extracts store, bill, item, product, quantity, and sales attributes.
3. It removes excluded products and converts transactions into baskets by store and bill.
4. FP-Growth or Apriori identifies frequent itemsets; association rules are calculated and scored with support, confidence, lift, and related metrics.
5. Approved results are stored in PostgreSQL for downstream recommendation experiences and reporting.
6. A run is observable, validated, and promoted only after data-quality and model/business checks pass.

## Data flow

```text
SQL Server warehouse (read-only)
  FactSalesTrxNew + DimDate + DimItem
             |
             v
  Extract → validate → cleanse → deduplicate → basketize
             |
             v
  Frequent-itemset mining → association-rule scoring → quality checks
             |
             v
  PostgreSQL: staging data, curated transactions, recommendation rules, run metadata
             |
             v
  Recommendation consumers, analytics, and operational monitoring
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
