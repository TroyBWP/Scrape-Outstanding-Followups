# CallPotential Outstanding Follow-Ups Scraper

Automated Playwright scraper that logs into CallPotential dashboard, scrapes the Outstanding Follow-Ups table, and saves snapshots to SQL Server.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Store Credentials in Windows Credential Manager

**CallPotential Login:**
- Open Windows Credential Manager
- Add a Generic Credential:
  - Internet or network address: `CallPotential`
  - User name: `Username`
  - Password: [Your CallPotential username]
- Add another Generic Credential:
  - Internet or network address: `CallPotential`
  - User name: `Password`
  - Password: [Your CallPotential password]

**Database credentials should already exist as `AIDevSQLDatabase` / `TroyAI`**

### 3. Create SQL Table

Run the SQL script to create the target table:

```bash
sqlcmd -S wpicsql01.westport.dom -E -i create_table.sql
```

Or execute `create_table.sql` manually in SSMS.

## Usage

Run the scraper:

```bash
python scrape_followups.py
```

The script will:
1. Retrieve credentials from Windows Credential Manager
2. Launch a headless Chromium browser
3. Navigate to CallPotential dashboard and login
4. Scrape the Outstanding Follow-Ups table (Location, Follow-Ups, and Unprocessed columns)
5. Truncate table for fresh snapshot
6. Join location names with `Westport_LocationData` to get `Lcode`
7. Insert snapshot into `Operations.Testing.OutstandingFollowUpSnapshot` via stored procedure

## Database Schema

**Table:** `Operations.Testing.OutstandingFollowUpSnapshot`

| Column | Type | Description |
|--------|------|-------------|
| ID | INT (PK) | Auto-incrementing primary key |
| dtSnapshot | DATETIME | Timestamp of when data was scraped |
| Lcode | VARCHAR(10) | Location code from Westport_LocationData |
| CallPotential_LocationName | VARCHAR(255) | Location name from CallPotential |
| UnprocessedFollowUps | INT | Number of outstanding follow-ups |
| UnprocessedCalls | INT | Number of unprocessed calls |

**Stored Procedure:** `Testing.GetOutstandingCPFollowUps`
- Automatically looks up Lcode from location name
- Inserts snapshot with all metrics
- Returns InsertedID and Lcode

## Troubleshooting

**Login fails:**
- Check credentials in Windows Credential Manager
- Verify the login form selectors haven't changed (inspect page with browser DevTools)
- Check `error_screenshot_*.png` for visual debugging

**Table not found:**
- The script looks for a table with "Location" and "Follow-Ups" columns
- If CallPotential UI changes, you may need to update the selectors in `scrape_table()`

**Lcode is NULL:**
- Means the location name from CallPotential doesn't match any record in `Connectors.CallPotential.locations_hist`
- Data still gets inserted, but Lcode will be NULL
- May need to update location mapping in `Westport_LocationData`

## Security

This scraper follows security best practices:
- **Credentials**: Stored in Windows Credential Manager (encrypted at rest)
- **SQL Injection Protection**: All database operations use parameterized queries via stored procedures
- **Least Privilege**: Database account has EXECUTE permission only on the stored procedure
- **No Secrets in Code**: No hardcoded credentials, tokens, or API keys
- **Code Review**: Approved by Xavier (technical) and Mira (security)

## Scheduling

To run this on a schedule, use Windows Task Scheduler:
1. Create a new task
2. Trigger: Daily at desired time
3. Action: Start a program
   - Program: `python`
   - Arguments: `"C:\Users\troyb\OneDrive - Westport Properties\Desktop\the-toolshed-new\Scrape Outstanding Follow Ups\scrape_followups.py"`
