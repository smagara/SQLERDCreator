## Dataless ERD generator for SQL Server
##
## Connect to a Microsoft SQL Server database, read the schema (including primary keys and foreign keys), 
## and generate an ERD using pandas-erd.
##

import shutil
import subprocess
import os
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect
from pandaserd import ERD
import pandas as pd
from dotenv import load_dotenv


def find_dot_executable():
    dot_cmd = shutil.which("dot")
    if dot_cmd:
        return dot_cmd

    fallback_paths = [
        Path("C:/Program Files/Graphviz/bin/dot.exe"),
        Path("C:/Program Files (x86)/Graphviz/bin/dot.exe"),
    ]

    for path in fallback_paths:
        if path.exists():
            return str(path)

    return None


def get_env(name, default=None):
    value = os.getenv(name, default)
    if isinstance(value, str):
        return value.strip()
    return value


def build_connection_string():
    # Backward compatible path: existing full connection string from .env.
    raw_connection = get_env("MSSQL_CONNECTION_STRING")
    if raw_connection:
        if raw_connection.lower().startswith("mssql+pyodbc://"):
            return raw_connection

        # Treat as ODBC connection string and wrap for SQLAlchemy.
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(raw_connection)}"

    host = get_env("MSSQL_HOST", "localhost")
    port = get_env("MSSQL_PORT", "1433")
    database = get_env("MSSQL_DATABASE")
    driver = get_env("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt = get_env("MSSQL_ENCRYPT", "yes")
    trust_server_certificate = get_env("MSSQL_TRUST_SERVER_CERTIFICATE", "yes")
    auth_mode = (get_env("MSSQL_AUTH_MODE", "windows") or "windows").lower()

    if not database:
        raise ValueError("MSSQL_DATABASE is required when MSSQL_CONNECTION_STRING is not set.")

    if auth_mode == "windows":
        return (
            f"mssql+pyodbc://@{host},{port}/{database}"
            f"?driver={quote_plus(driver)}"
            f"&trusted_connection=yes"
            f"&Encrypt={encrypt}"
            f"&TrustServerCertificate={trust_server_certificate}"
        )

    if auth_mode == "sql":
        uid = get_env("MSSQL_UID")
        pwd = get_env("MSSQL_PWD")
        if not uid or not pwd:
            raise ValueError("MSSQL_UID and MSSQL_PWD are required when MSSQL_AUTH_MODE=sql.")

        return (
            f"mssql+pyodbc://{quote_plus(uid)}:{quote_plus(pwd)}@{host},{port}/{database}"
            f"?driver={quote_plus(driver)}"
            f"&Encrypt={encrypt}"
            f"&TrustServerCertificate={trust_server_certificate}"
        )

    raise ValueError("MSSQL_AUTH_MODE must be either 'windows' or 'sql'.")

# ---------- 1. Database Connection ----------
# Requires: pip install sqlalchemy pyodbc pandas pandaserd python-dotenv
load_dotenv()

try:
    connection_string = build_connection_string()
    engine = create_engine(connection_string)
    inspector = inspect(engine)
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    exit(1)

# ---------- 2. Get All Tables Across Schemas ----------
try:
    # SQL Server objects are often not in dbo, so enumerate all user schemas.
    ignored_schemas = {"information_schema", "sys"}
    schemas = [s for s in inspector.get_schema_names() if s.lower() not in ignored_schemas]

    table_refs = []
    for schema in schemas:
        for table in inspector.get_table_names(schema=schema):
            table_refs.append((schema, table))

    if not table_refs:
        print("⚠ No tables found in the database.")
        exit(0)
except Exception as e:
    print(f"❌ Failed to retrieve tables: {e}")
    exit(1)

# ---------- 3. Create ERD Object ----------
erd = ERD()
table_name_map = {}

for schema, table in table_refs:
    # Dots in identifiers break Graphviz unless quoted; use a safe identifier.
    table_name_map[(schema, table)] = f"{schema}__{table}"

# ---------- 4. Add Tables Without Data ----------
for schema, table in table_refs:
    try:
        table_name = table_name_map[(schema, table)]

        # Get column names from schema
        columns = [col["name"] for col in inspector.get_columns(table, schema=schema)]
        # Create an *empty* DataFrame with just column names
        df_empty = pd.DataFrame(columns=columns)

        # Get primary key(s)
        pk_info = inspector.get_pk_constraint(table, schema=schema)
        pk_cols = pk_info.get("constrained_columns", [])

        if pk_cols:
            erd.add_table(df_empty, table_name=table_name, primary_key=pk_cols[0])
        else:
            erd.add_table(df_empty, table_name=table_name)

    except Exception as e:
        print(f"⚠ Skipping table '{schema}.{table}' due to schema read error: {e}")

# ---------- 5. Add Relationships from Foreign Keys ----------
for schema, table in table_refs:
    try:
        child_table_name = table_name_map[(schema, table)]
        fks = inspector.get_foreign_keys(table, schema=schema)
        for fk in fks:
            parent_schema = fk.get("referred_schema") or schema
            parent_table = fk.get("referred_table")
            parent_cols = fk.get("referred_columns") or []
            child_cols = fk.get("constrained_columns") or []

            if not parent_table or not parent_cols or not child_cols:
                continue

            parent_key = (parent_schema, parent_table)
            parent_table_name = table_name_map.get(parent_key)
            if not parent_table_name:
                continue

            parent_col = parent_cols[0]
            child_col = child_cols[0]
            erd.create_rel(child_table_name, parent_table_name, left_on=child_col, right_on=parent_col)
    except Exception as e:
        print(f"⚠ Could not get foreign keys for '{schema}.{table}': {e}")

# ---------- 6. Render ERD ----------
try:
    dot_filename = "mssql_schema_only_erd.dot"
    png_filename = "mssql_schema_only_erd.png"

    erd.write_to_file(dot_filename)
    print(f"✅ ERD DOT saved as {dot_filename}")

    dot_cmd = find_dot_executable()
    if dot_cmd:
        subprocess.run([dot_cmd, "-Tpng", dot_filename, "-o", png_filename], check=True)
        print(f"✅ ERD PNG saved as {png_filename}")
    else:
        print("⚠ Graphviz 'dot' command not found, PNG was not generated.")
        print("   Install Graphviz and re-run. On Windows: winget install Graphviz.Graphviz")
except Exception as e:
    print(f"❌ Failed to render ERD: {e}")
