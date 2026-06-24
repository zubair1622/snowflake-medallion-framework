CREATE OR REPLACE PROCEDURE PROC_TABLE(
    P_DATABASE STRING,
    P_SCHEMA STRING,
    P_TABLE_DEFINITIONS ARRAY
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
from snowflake.snowpark import Session

def main(session: Session, P_DATABASE: str, P_SCHEMA: str, P_TABLE_DEFINITIONS: list):
    """
    P_TABLE_DEFINITIONS must be an array of OBJECT_CONSTRUCT elements, for example:
    ARRAY_CONSTRUCT(
        OBJECT_CONSTRUCT('table_name', 'bronze_customers_delta', 'columns', 'customer_id INT, customer_name STRING, start_date TIMESTAMP_NTZ,End_date TIMESTAMP_NTZ, delete_flag STRING'),
        OBJECT_CONSTRUCT('table_name', 'bronze_products_delta', 'columns', 'product_id STRING, product_name STRING, start_date TIMESTAMP_NTZ,End_date TIMESTAMP_NTZ, delete_flag STRING')
    )
    """

    created_tables = []

    for tbl in P_TABLE_DEFINITIONS:
        table_name = tbl["table_name"]
        columns = tbl["columns"]

        full_table_name = f"{P_DATABASE}.{P_SCHEMA}.{table_name}"
        print(f"📘 Creating table: {full_table_name}")

        session.sql(f"""
            CREATE OR REPLACE TABLE {full_table_name} (
                {columns}
            )
        """).collect()

        created_tables.append(full_table_name)

    print(f"✅ Successfully created {len(created_tables)} table(s)")
    return f"✅ Successfully created {len(created_tables)} table(s): {', '.join(created_tables)}"
$$;
