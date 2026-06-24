CREATE OR REPLACE PROCEDURE PROC_CREATE_SILVER(
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
from snowflake.snowpark.functions import col, sql_expr

def main(session: Session, DB: str, SCHEMA: str, TABLE_MAPPINGS: list):

    successes = []
    failures = []

    load_timestamp = sql_expr("CURRENT_TIMESTAMP()::TIMESTAMP_NTZ")

    for mapping in TABLE_MAPPINGS:

        try:

            bronze_table = mapping.get("bronze_table")
            silver_table = mapping.get("silver_table")

            if not bronze_table or not silver_table:
                failures.append(f"Invalid Mapping: {mapping}")
                continue

            bronze_full = f"{DB}.{SCHEMA}.{bronze_table}"
            silver_full = f"{DB}.{SCHEMA}.{silver_table}"

            # Step 1: Read Bronze Table
            df = session.table(bronze_full)

            # Step 2: Dynamic Data Cleaning
            schema_info = df.schema.fields

            for field in schema_info:
                column_name = field.name
                column_type = str(field.datatype).upper()

                # Trim String Columns
                if "STRING" in column_type or "TEXT" in column_type:
                    df = df.with_column(
                        column_name,
                        sql_expr(f"TRIM({column_name})")
                    )

                # Standardize Date/Timestamp
                elif any(dtype in column_type for dtype in ["DATE", "TIMESTAMP"]):
                    df = df.with_column(
                        column_name,
                        col(column_name).cast("TIMESTAMP_NTZ")
                    )

            # Step 3: Remove Duplicate Records
            df = df.distinct()

            # Step 4: Add LOAD_DATE
            df = df.with_column("LOAD_DATE", load_timestamp)

            # Step 5: Save To Silver
            df.write.mode("overwrite").save_as_table(silver_full)

            successes.append(silver_full)

        except Exception as e:
            failures.append(f"{mapping.get('bronze_table', 'UNKNOWN')}: {str(e)}")

    # Final Status
    if failures:
        return (
            f"Partial Success. "
            f"Created {len(successes)} tables. "
            f"Failures: {failures}"
        )

    return (
        f"Success. "
        f"Created {len(successes)} tables: "
        f"{', '.join(successes)}"
    )
$$;
