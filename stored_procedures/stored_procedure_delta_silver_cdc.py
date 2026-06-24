CREATE OR REPLACE PROCEDURE PROC_DELTA_SILVER_CDC(
    DB STRING,
    SCHEMA STRING,
    TABLE_MAPPINGS ARRAY
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
from snowflake.snowpark import Session

def main(session: Session, DB, SCHEMA, TABLE_MAPPINGS):

    MAX_DATE = "2999-12-31 00:00:00"
    results = []

    for mapping in TABLE_MAPPINGS:

        bronze = f"{DB}.{SCHEMA}.{mapping['bronze_table']}"
        silver = f"{DB}.{SCHEMA}.{mapping['silver_table']}"
        key = mapping['key_column']

        # ---------------------------------------
        # 1. GET COMMON COLUMNS
        # ---------------------------------------
        bronze_cols = session.table(bronze).columns
        silver_cols = session.table(silver).columns

        common_cols = [c for c in bronze_cols if c in silver_cols]

        compare_cols = [
            c for c in common_cols
            if c.upper() not in [key.upper(), "START_DATE", "END_DATE", "LOAD_DATE", "DELETE_FLAG"]
        ]

        insert_cols = [
            c for c in common_cols
            if c.upper() != "LOAD_DATE"
        ]

        insert_col_list = ", ".join([f'"{c}"' for c in insert_cols])
        select_col_list = ", ".join([f'cs."{c}"' for c in insert_cols])

        # ---------------------------------------
        # 2. CHANGE CONDITION
        # ---------------------------------------
        if compare_cols:
            change_condition = " OR ".join([
                f"COALESCE(TO_VARCHAR(s.\"{c}\"),'') <> COALESCE(TO_VARCHAR(b.\"{c}\"),'')"
                for c in compare_cols
            ])
        else:
            change_condition = "FALSE"

        # ---------------------------------------
        # 3. CREATE CHANGE SET (TEMP TABLE)
        # ---------------------------------------
        change_set = f"{silver}_CHANGE_SET"

        session.sql(f"""
            CREATE OR REPLACE TRANSIENT TABLE {change_set} AS
            SELECT
                b.*,
                CASE
                    WHEN b.DELETE_FLAG = 'Y' AND s."{key}" IS NOT NULL THEN 'DELETE'
                    WHEN s."{key}" IS NULL AND b.DELETE_FLAG = 'N' THEN 'NEW'
                    WHEN b.DELETE_FLAG = 'N' AND s."{key}" IS NOT NULL AND ({change_condition}) THEN 'UPDATE'
                    ELSE 'UNCHANGED'
                END AS CHANGE_TYPE
            FROM {bronze} b
            LEFT JOIN {silver} s
              ON b."{key}" = s."{key}"
             AND s.END_DATE = '{MAX_DATE}'
        """).collect()

        # ---------------------------------------
        # 4. CLOSE RECORDS (DELETE + UPDATE)
        # ---------------------------------------
        session.sql(f"""
            MERGE INTO {silver} s
            USING {change_set} cs
            ON s."{key}" = cs."{key}"
               AND s.END_DATE = '{MAX_DATE}'
            WHEN MATCHED AND cs.CHANGE_TYPE IN ('DELETE','UPDATE')
            THEN UPDATE SET
                s.END_DATE = cs.START_DATE,
                s.LOAD_DATE = CURRENT_TIMESTAMP(),
                s.DELETE_FLAG = 'Y'
        """).collect()

        # ---------------------------------------
        # 5. INSERT NEW + UPDATED RECORDS
        # ---------------------------------------
        session.sql(f"""
            INSERT INTO {silver} ({insert_col_list}, LOAD_DATE)
            SELECT
                {select_col_list},
                CURRENT_TIMESTAMP()
            FROM {change_set} cs
            WHERE cs.CHANGE_TYPE IN ('NEW','UPDATE')
        """).collect()

        # ---------------------------------------
        # 6. CLEANUP
        # ---------------------------------------
        session.sql(f"DROP TABLE IF EXISTS {change_set}").collect()

        results.append(f"{mapping['silver_table']} processed")

    return "CDC Completed Successfully (Change-Set Approach): " + ", ".join(results)

$$;
