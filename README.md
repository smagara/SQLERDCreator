# SQL Server Schema-Only ERD Generator

Generate an Entity Relationship Diagram (ERD) for a SQL Server database **without reading table data**.

This project is aimed at database developers and DBAs who want a quick schema map from system metadata (tables, columns, PKs, FKs).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## What It Does

- Connects to SQL Server via SQLAlchemy + pyodbc.
- Enumerates user schemas (excluding `sys` and `information_schema`).
- Reads table/column/PK/FK metadata.
- Produces:
  - `mssql_schema_only_erd.dot` (Graphviz DOT)
  - `mssql_schema_only_erd.png` (rendered image, if Graphviz is available)

## Prerequisites

## 1. Python

- Python 3.10+ recommended

## 2. ODBC Driver for SQL Server

Install at least one of:

- ODBC Driver 17 for SQL Server
- ODBC Driver 18 for SQL Server

On Windows, you can verify installed drivers in ODBC Data Source Administrator.

## 3. Graphviz (for PNG output)

The script writes a DOT file regardless. PNG generation requires Graphviz `dot`.

Install on Windows:

```powershell
winget install Graphviz.Graphviz
```

## 4. Python Dependencies

Install project dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Setup

Configure database access in `.env` (the script loads this automatically).

You can choose either:

- A full connection string via `MSSQL_CONNECTION_STRING`
- Parameterized settings via `MSSQL_AUTH_MODE` + host/database/driver variables

## .env Configuration Patterns

## Option A: Full Connection String (existing compatible mode)

Use your current ODBC connection string directly:

```dotenv
MSSQL_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=.;DATABASE=yourDBName;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
```

The script will convert it to a SQLAlchemy-compatible format.

## Option B: SQL Authentication (uid/pwd)

```dotenv
MSSQL_AUTH_MODE=sql
MSSQL_HOST=localhost
MSSQL_PORT=21433
MSSQL_DATABASE=yourDBName
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_UID=sa
MSSQL_PWD=YourStrongPassword123
MSSQL_ENCRYPT=yes
MSSQL_TRUST_SERVER_CERTIFICATE=yes
```

## Option C: Windows Authentication

```dotenv
MSSQL_AUTH_MODE=windows
MSSQL_HOST=.
MSSQL_PORT=1433
MSSQL_DATABASE=yourDBName
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_ENCRYPT=yes
MSSQL_TRUST_SERVER_CERTIFICATE=yes
```

When `MSSQL_CONNECTION_STRING` is set, it takes precedence over mode-based settings.

## URL Reference Patterns (for direct SQLAlchemy URLs)

## SQL Authentication

```python
connection_string = (
    "mssql+pyodbc://<user>:<password>@<host>,<port>/<database>"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)
```

## Windows Integrated Security (Trusted Connection)

```python
connection_string = (
    "mssql+pyodbc://@<host>,<port>/<database>"
    "?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
)
```

## ODBC Driver 18 with Encryption

If you use ODBC 18, specify encryption options explicitly as needed by your environment:

```python
connection_string = (
    "mssql+pyodbc://<user>:<password>@<host>,<port>/<database>"
    "?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
)
```

Adjust `TrustServerCertificate` per security policy.

## Usage

Run:

```powershell
python createERD.py
```

Expected output:

- `mssql_schema_only_erd.dot`
- `mssql_schema_only_erd.png` (if Graphviz is found)

## Understanding the Output

- The diagram node IDs are sanitized to `schema__table` for Graphviz compatibility.
- Relationships are generated from foreign key metadata.
- Column data types may appear as generic types (`object`) because the script builds empty dataframes from schema names only.

## Troubleshooting

## "No tables found"

Possible causes:

- Connected to the wrong database.
- Login has limited metadata visibility.
- Only system schemas are visible.

Checks:

- Validate database name in connection string.
- Ensure principal has access to target schemas/tables.
- Test with SSMS/Azure Data Studio using same login.

## "Graphviz 'dot' command not found"

- Install Graphviz with `winget` (above).
- Reopen terminal/VS Code so updated PATH is loaded.
- This script also checks common Windows install paths directly.

## ODBC/Driver Errors

- Confirm installed driver version matches connection string (`17` vs `18`).
- Ensure SQL Server TCP port is reachable.
- For containers, verify host/port mapping.

## Security Notes for DBAs

- Prefer least-privilege logins with metadata read access.
- Avoid committing credentials in source control.
- Consider moving connection details to environment variables before team use.

## File Overview

- [createERD.py](createERD.py): main script
- [requirements.txt](requirements.txt): Python dependencies
- [mssql_schema_only_erd.dot](mssql_schema_only_erd.dot): generated Graphviz source
- [mssql_schema_only_erd.png](mssql_schema_only_erd.png): generated diagram image
