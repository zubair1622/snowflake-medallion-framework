CREATE OR REPLACE PROCEDURE PROC_COPY_BRONZE(
    P_STAGE STRING,
    P_FILE_FORMAT STRING,
    P_TABLES ARRAY
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
from datetime import datetime, timedelta, timezone
from snowflake.snowpark import Session

def main(
    session: Session,
    P_STAGE: str,
    P_FILE_FORMAT: str,
    P_TABLES: list
):

    success = []
    failed = []
    skipped = []
    details = []

    # --------------------------------------------------
    # Folder Path
    # --------------------------------------------------

    folder_path = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).strftime("%Y/%b/%d/").title()

    details.append(
        f"Folder Path Used: {folder_path}"
    )

    # --------------------------------------------------
    # Process Each Table
    # --------------------------------------------------

    for tbl in P_TABLES:

        table_name = tbl.get("table_name")
        subfolder = tbl.get("subfolder")

        if not table_name or not subfolder:

            failed.append(
                f"Invalid Mapping: {tbl}"
            )

            continue

        source_path = (
            f"@{P_STAGE}/"
            f"{subfolder}/"
            f"Delta_load/"
            f"csv_files/"
            f"{folder_path}"
        )

        try:

            # ------------------------------------------
            # Step 1: Check Files Available
            # ------------------------------------------

            files = session.sql(
                f"LIST {source_path}"
            ).collect()

            parquet_files = []

            for file in files:

                file_name = str(file[0])

                if file_name.lower().endswith(".parquet"):

                    parquet_files.append(file_name)

            details.append(
                f"{table_name} -> {source_path}"
            )

            details.append(
                f"{table_name} -> Parquet Files Found: {len(parquet_files)}"
            )

            # ------------------------------------------
            # No Parquet Files Found
            # ------------------------------------------

            if len(parquet_files) == 0:

                skipped.append(
                    f"{table_name} (No parquet files found)"
                )

                continue

            # ------------------------------------------
            # Log Found Files
            # ------------------------------------------

            for file_name in parquet_files:

                details.append(
                    f"{table_name} -> FILE FOUND: {file_name}"
                )

            # ------------------------------------------
            # Step 2: Truncate Bronze Table
            # ------------------------------------------

            session.sql(
                f"TRUNCATE TABLE {table_name}"
            ).collect()

            details.append(
                f"{table_name} truncated successfully"
            )

            # ------------------------------------------
            # Step 3: Load Data
            # ------------------------------------------

            copy_query = f"""
            COPY INTO {table_name}
            FROM {source_path}
            FILE_FORMAT = (
                FORMAT_NAME = {P_FILE_FORMAT}
            )
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
            """

            copy_result = session.sql(
                copy_query
            ).collect()

            details.append(
                f"{table_name} COPY RESULT: {copy_result}"
            )

            success.append(table_name)

        except Exception as e:

            failed.append(
                f"{table_name}: {str(e)}"
            )

    # --------------------------------------------------
    # Final Summary
    # --------------------------------------------------

    return f'''
SUCCESS TABLES:
{success}

FAILED TABLES:
{failed}

SKIPPED TABLES:
{skipped}

DETAILS:
{chr(10).join(details)}
'''
$$;
