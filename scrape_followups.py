"""
Scrape Outstanding Follow-Ups from CallPotential Dashboard
Saves snapshot to Operations.Testing.OutstandingFollowUpSnapshot
"""

import asyncio
import pyodbc
import keyring
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import sys


class CallPotentialScraper:
    """Scrapes outstanding follow-ups from CallPotential dashboard"""

    def __init__(self):
        self.url = "https://sys.callpotential.com/ui/v2/dashboard"
        self.username = None
        self.password = None
        self.db_connection = None

    def _get_credentials(self):
        """Retrieve CallPotential credentials from Windows Credential Manager"""
        print("Retrieving credentials from Windows Credential Manager...")
        self.username = keyring.get_password('CallPotential', 'Username')
        self.password = keyring.get_password('CallPotential', 'Password')

        if not self.username or not self.password:
            raise ValueError(
                "CallPotential credentials not found in Windows Credential Manager.\n"
                "Please store credentials with:\n"
                "  Service: CallPotential\n"
                "  Username: Username (for the actual username)\n"
                "  Username: Password (for the actual password)"
            )

    def _get_db_connection(self):
        """Establish SQL Server connection"""
        print("Connecting to SQL Server...")
        password = keyring.get_password('AIDevSQLDatabase', 'TroyAI')

        if not password:
            raise ValueError("Database credentials not found in Windows Credential Manager")

        conn_str = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER=wpicsql01.westport.dom;'
            f'DATABASE=Operations;'
            f'UID=TroyAI;'
            f'PWD={password}'
        )

        self.db_connection = pyodbc.connect(conn_str)
        print("Database connection established")

    async def login(self, page):
        """Authenticate to CallPotential"""
        print(f"Navigating to {self.url}...")
        await page.goto(self.url, wait_until='networkidle', timeout=30000)

        # Wait for login form to appear
        print("Waiting for login form...")
        await page.wait_for_selector('input[name="username"]', timeout=10000)

        # Fill in username
        print("Entering credentials...")
        await page.fill('input[name="username"]', self.username)
        await page.fill('input[type="password"]', self.password)

        # Submit form
        print("Submitting login...")
        await page.click('button[type="submit"]')

        # Wait for dashboard to load
        print("Waiting for dashboard to load...")
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(5)  # Additional wait for dynamic content to populate

        print("Login successful")

    async def scrape_table(self, page):
        """Scrape the outstanding follow-ups table"""
        print("Locating follow-ups table...")

        # Wait for page to fully load
        await asyncio.sleep(3)

        # Check for iframes
        frames = page.frames
        print(f"Found {len(frames)} frames on page")

        # Try to find the table in each frame
        target_frame = None
        table = None

        for idx, frame in enumerate(frames):
            print(f"Checking frame {idx + 1}...")
            tables = await frame.query_selector_all('table')

            for t in tables:
                headers = await t.query_selector_all('th')
                if headers:
                    header_texts = [await h.inner_text() for h in headers]
                    header_clean = ' '.join(header_texts).upper()

                    # Look for the table with LOCATION and FOLLOW-UPS headers
                    if 'LOCATION' in header_clean and 'FOLLOW' in header_clean:
                        print(f"  Found target table in frame {idx + 1}!")
                        print(f"  Headers: {header_texts}")
                        table = t
                        break

            if table:
                break

        if not table:
            await page.screenshot(path='no_table_found.png')
            raise ValueError("Could not find table with LOCATION and FOLLOW-UPS columns. Screenshot: no_table_found.png")

        # Wait for table rows to populate AND for real data to load (not just zeros)
        print("Waiting for table data to load...")
        max_retries = 20
        rows = []
        for attempt in range(max_retries):
            # Try tbody first, then all tr elements
            rows = await table.query_selector_all('tbody tr')
            if len(rows) == 0:
                # Try without tbody - filter out header rows properly
                all_rows = await table.query_selector_all('tr')
                rows = []
                for r in all_rows:
                    if await r.query_selector('td'):
                        rows.append(r)

            # Check if we have rows AND that they contain real data (not all zeros)
            if len(rows) > 0:
                # Check across ALL rows to see if we have ANY non-zero values
                # This is more robust since legitimate zeros are possible
                has_real_data = False
                total_nonzero = 0

                for check_row in rows:
                    cells = await check_row.query_selector_all('td')
                    if len(cells) > 1:
                        # Check if any numeric cells have non-zero values
                        for cell in cells[1:]:  # Skip location column
                            text = await cell.inner_text()
                            cleaned = text.strip().replace(',', '')
                            if cleaned.isdigit() and int(cleaned) > 0:
                                total_nonzero += 1

                # If we have at least some non-zero values across the entire table, we have real data
                # Using a threshold: at least 5% of rows should have non-zero values OR at least 10 non-zero values total
                threshold = max(10, int(len(rows) * 0.05))
                if total_nonzero >= threshold:
                    has_real_data = True
                    print(f"Table populated with {len(rows)} rows containing real data ({total_nonzero} non-zero values found)")
                    break
                else:
                    print(f"  Attempt {attempt + 1}/{max_retries}: Table has {len(rows)} rows but insufficient non-zero data ({total_nonzero} found, need {threshold}), waiting...")
            else:
                print(f"  Attempt {attempt + 1}/{max_retries}: Table empty, waiting...")

            await asyncio.sleep(3)  # Increased wait time between checks
        else:
            # Take screenshot for debugging
            await page.screenshot(path='empty_table_debug.png')
            raise ValueError("Table did not populate with real data after waiting. Screenshot saved to empty_table_debug.png")

        # Get headers
        headers = await table.query_selector_all('th')
        header_texts = [await h.inner_text() for h in headers]

        print(f"Table headers: {header_texts}")

        # Find column indices - looking for LOCATION, FOLLOW-UPS, and UNPROCESSED
        location_idx = None
        followup_idx = None
        unprocessed_idx = None

        for i, h in enumerate(header_texts):
            h_clean = h.replace('\n', ' ').strip().upper()
            if 'LOCATION' in h_clean:
                location_idx = i
                print(f"  Found LOCATION at column {i}")
            if 'FOLLOW-UP' in h_clean or 'FOLLOW UP' in h_clean:
                followup_idx = i
                print(f"  Found FOLLOW-UPS at column {i}")
            if 'UNPROCESSED' in h_clean:
                unprocessed_idx = i
                print(f"  Found UNPROCESSED at column {i}")

        if location_idx is None or followup_idx is None or unprocessed_idx is None:
            raise ValueError(f"Could not find required columns. Headers: {header_texts}")

        # rows already fetched in the retry loop above (variable 'rows')
        print(f"Processing {len(rows)} rows...")

        data = []

        for row in rows:
            cells = await row.query_selector_all('td')

            if len(cells) > max(location_idx, followup_idx, unprocessed_idx):
                # Location is inside a <p class="location-name"> tag
                location_cell = cells[location_idx]
                location_p = await location_cell.query_selector('p.location-name')
                if location_p:
                    location = (await location_p.inner_text()).strip()
                else:
                    location = (await location_cell.inner_text()).strip()

                # Follow-ups and Unprocessed are in td.digit-cell
                followups = (await cells[followup_idx].inner_text()).strip()
                unprocessed = (await cells[unprocessed_idx].inner_text()).strip()

                # Clean up values (remove commas, convert to int)
                followups_clean = followups.replace(',', '').replace(' ', '')
                unprocessed_clean = unprocessed.replace(',', '').replace(' ', '')

                try:
                    followups_int = int(followups_clean)
                    unprocessed_int = int(unprocessed_clean)
                    data.append({
                        'location': location,
                        'followups': followups_int,
                        'unprocessed': unprocessed_int
                    })
                except ValueError:
                    print(f"Warning: Could not convert values to integer for location '{location}'")
                    continue

        if not data:
            raise ValueError("No valid data found in follow-ups table")

        print(f"Scraped {len(data)} records")
        return data

    def save_to_database(self, data):
        """Save scraped data to SQL using stored procedure"""
        print("Processing data and saving to database...")

        cursor = None
        try:
            cursor = self.db_connection.cursor()
            snapshot_time = datetime.now()

            # Truncate table BEFORE processing any records
            print("Truncating table for fresh snapshot...")
            try:
                cursor.execute("EXEC Testing.TruncateOutstandingFollowUpSnapshot")
                self.db_connection.commit()
                print("Table truncated successfully")
            except Exception as e:
                print(f"ERROR during truncate: {e}")
                raise

            print(f"Starting to insert {len(data)} records...")
            inserted = 0
            failed = 0
            locations_without_lcode = []

            for idx, record in enumerate(data, 1):
                location_name = record['location']
                followups = record['followups']
                unprocessed = record['unprocessed']

                try:
                    # Call stored procedure (no longer need truncate_first parameter)
                    cursor.execute(
                        "EXEC Testing.GetOutstandingCPFollowUps ?, ?, ?, ?",
                        (snapshot_time, location_name, followups, unprocessed)
                    )

                    # Get result (InsertedID and Lcode)
                    result = cursor.fetchone()
                    if result:
                        _, lcode = result
                        if lcode is None:
                            locations_without_lcode.append(location_name)
                            # Skip inserting records without Lcode - rollback this insert
                            self.db_connection.rollback()
                            failed += 1
                            continue
                        else:
                            inserted += 1
                            # CRITICAL: Must commit after each stored procedure call
                            self.db_connection.commit()

                    # Progress indicator every 50 records
                    if idx % 50 == 0:
                        print(f"  Processed {idx}/{len(data)} records...")

                except Exception as e:
                    print(f"Error inserting record for '{location_name}': {e}")
                    self.db_connection.rollback()  # Rollback failed insert
                    failed += 1

            # Summary
            print(f"\nInsert complete: {inserted} records saved, {failed} failed")

        except Exception as e:
            print(f"FATAL ERROR in save_to_database: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
                print("Database cursor closed")

        if locations_without_lcode:
            print(f"\nWarning: {len(locations_without_lcode)} location(s) without Lcode:")
            for loc in locations_without_lcode[:10]:  # Show first 10
                print(f"  - {loc}")
            if len(locations_without_lcode) > 10:
                print(f"  ... and {len(locations_without_lcode) - 10} more")

    async def run(self):
        """Main execution flow"""
        try:
            # Get credentials
            self._get_credentials()

            # Connect to database
            self._get_db_connection()

            # Launch browser and scrape
            async with async_playwright() as p:
                print("Launching headless browser...")
                browser = await p.chromium.launch(headless=True)

                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )

                page = await context.new_page()

                try:
                    # Login
                    await self.login(page)

                    # Scrape table
                    data = await self.scrape_table(page)

                    # Save to database
                    self.save_to_database(data)

                    print("\nScrape completed successfully!")

                except PlaywrightTimeout as e:
                    print(f"Timeout error: {e}")
                    # Take screenshot for debugging
                    screenshot_path = f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"Screenshot saved to {screenshot_path}")
                    raise

                finally:
                    await browser.close()

        finally:
            if self.db_connection:
                self.db_connection.close()
                print("Database connection closed")


def main():
    """Entry point"""
    scraper = CallPotentialScraper()
    asyncio.run(scraper.run())


if __name__ == "__main__":
    main()
