CREATE OR REPLACE PROCEDURE PROC_STAGING(
      P_DATABASE STRING,
      P_SCHEMA STRING,
      P_FILE_FORMAT_NAME STRING,
      P_FILE_FORMAT_TYPE STRING,
      P_STAGE_NAME STRING,
      P_STAGE_URL STRING,
      P_STORAGE_INTEGRATION STRING
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'main'
AS
$$
from snowflake.snowpark import Session

def main(session: Session,
         P_DATABASE: str,
         P_SCHEMA: str,
         P_FILE_FORMAT_NAME: str,
         P_FILE_FORMAT_TYPE: str,
         P_STAGE_NAME: str,
         P_STAGE_URL: str,
         P_STORAGE_INTEGRATION: str):


    # Step 1: Create or Replace File Format 
    
    session.sql(f"""
        CREATE OR REPLACE FILE FORMAT {P_DATABASE}.{P_SCHEMA}.{P_FILE_FORMAT_NAME}
        TYPE = '{P_FILE_FORMAT_TYPE}'
    """).collect()

    
    # Step 2: Create or Replace Stage 
    
    session.sql(f"""
        CREATE OR REPLACE STAGE {P_DATABASE}.{P_SCHEMA}.{P_STAGE_NAME}
        URL = '{P_STAGE_URL}'
        STORAGE_INTEGRATION = {P_STORAGE_INTEGRATION}
        FILE_FORMAT = {P_DATABASE}.{P_SCHEMA}.{P_FILE_FORMAT_NAME}
    """).collect()

    return f"Stage '{P_DATABASE}.{P_SCHEMA}.{P_STAGE_NAME}' created successfully using file format '{P_FILE_FORMAT_NAME}' ({P_FILE_FORMAT_TYPE})."
$$;
