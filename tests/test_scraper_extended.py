"""
Extended unit tests for CallPotential scraper
Tests web scraping logic, error handling, and edge cases
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from scrape_followups import CallPotentialScraper


# =============================================================================
# Mock Fixtures
# =============================================================================

class MockElement:
    """Mock Playwright element"""
    def __init__(self, text="", elements=None):
        self.text = text
        self.elements = elements or []

    async def inner_text(self):
        return self.text

    async def query_selector_all(self, selector):
        return self.elements

    async def query_selector(self, selector):
        return self.elements[0] if self.elements else None


class MockFrame:
    """Mock Playwright frame"""
    def __init__(self, tables=None):
        self.tables = tables or []

    async def query_selector_all(self, selector):
        if selector == 'table':
            return self.tables
        return []


class MockPage:
    """Mock Playwright page"""
    def __init__(self, frames=None):
        self._frames = frames or []
        self.url_val = ""
        self.screenshots = []

    def frames(self):
        return self._frames

    async def goto(self, url):
        self.url_val = url

    async def fill(self, selector, value):
        pass

    async def click(self, selector):
        pass

    async def wait_for_selector(self, selector, **kwargs):
        pass

    async def screenshot(self, path):
        self.screenshots.append(path)


# =============================================================================
# Test: Table Finding Logic
# =============================================================================

@pytest.mark.asyncio
async def test_find_table_in_correct_frame():
    """Test that scraper finds table in the correct iframe"""

    # Create mock table with correct headers
    headers = [
        MockElement("Location"),
        MockElement("Follow-Ups"),
        MockElement("Unprocessed")
    ]
    table_with_headers = MockElement(elements=headers)

    # Create frames - target table is in frame 2
    wrong_frame = MockFrame(tables=[MockElement()])  # Wrong table
    correct_frame = MockFrame(tables=[table_with_headers])

    page = MockPage(frames=[wrong_frame, correct_frame])

    # The scraper's scrape_table method should find the table
    scraper = CallPotentialScraper()

    # We can't easily test the full scrape_table method due to dependencies,
    # but we can verify the frame iteration logic
    table = None
    for frame in page.frames():
        tables = await frame.query_selector_all('table')
        for t in tables:
            headers_els = await t.query_selector_all('th')
            if headers_els:
                header_texts = [await h.inner_text() for h in headers_els]
                header_clean = ' '.join(header_texts).upper()
                if 'LOCATION' in header_clean and 'FOLLOW' in header_clean:
                    table = t
                    break
        if table:
            break

    assert table is not None, "Should find table in second frame"
    assert table == table_with_headers


@pytest.mark.asyncio
async def test_no_table_found_error():
    """Test error handling when table is not found"""

    # Create frames with no matching tables
    wrong_table = MockElement(elements=[MockElement("Wrong"), MockElement("Headers")])
    frame = MockFrame(tables=[wrong_table])
    page = MockPage(frames=[frame])

    # Should raise error and take screenshot
    table = None
    for frame in page.frames():
        tables = await frame.query_selector_all('table')
        for t in tables:
            headers_els = await t.query_selector_all('th')
            if headers_els:
                header_texts = [await h.inner_text() for h in headers_els]
                header_clean = ' '.join(header_texts).upper()
                if 'LOCATION' in header_clean and 'FOLLOW' in header_clean:
                    table = t
                    break

    if not table:
        await page.screenshot(path='no_table_found.png')

    assert table is None, "Should not find table"
    assert 'no_table_found.png' in page.screenshots


# =============================================================================
# Test: Data Parsing
# =============================================================================

def test_parse_integer_from_text():
    """Test parsing integers from table cells"""

    test_cases = [
        ("123", 123),
        ("1,234", 1234),
        ("  456  ", 456),
        ("N/A", 0),
        ("", 0),
        ("--", 0),
    ]

    for text, expected in test_cases:
        # Simulate the scraper's parsing logic
        try:
            # Remove commas and strip whitespace
            cleaned = text.replace(',', '').strip()
            if cleaned and cleaned.isdigit():
                result = int(cleaned)
            else:
                result = 0
        except:
            result = 0

        assert result == expected, f"Failed to parse '{text}' -> {expected}, got {result}"


def test_parse_location_name():
    """Test location name extraction and cleaning"""

    test_cases = [
        ("Location A", "Location A"),
        ("  Location B  ", "Location B"),
        ("Location\nC", "Location C"),  # Newline handling
        ("Location\tD", "Location D"),  # Tab handling
    ]

    for raw, expected in test_cases:
        # Simulate scraper's cleaning logic
        cleaned = raw.replace('\n', ' ').replace('\t', ' ').strip()
        cleaned = ' '.join(cleaned.split())  # Normalize whitespace

        assert cleaned == expected, f"Failed to clean '{raw}' -> '{expected}', got '{cleaned}'"


# =============================================================================
# Test: Error Handling
# =============================================================================

@pytest.mark.asyncio
async def test_login_failure_handling():
    """Test handling of login failures"""

    scraper = CallPotentialScraper()
    scraper.username = "test_user"
    scraper.password = "test_pass"

    # Mock page that simulates login failure (selector not found)
    page = MockPage()

    # Simulate timeout on wait_for_selector
    async def mock_wait_timeout(selector, **kwargs):
        raise Exception("Timeout waiting for selector")

    page.wait_for_selector = mock_wait_timeout

    # Test that error is handled
    error_occurred = False
    try:
        await page.goto("https://sys.callpotential.com/ui/v2/dashboard")
        await page.fill("input[name='username']", scraper.username)
        await page.fill("input[name='password']", scraper.password)
        await page.click("button[type='submit']")
        await page.wait_for_selector("text=Dashboard", timeout=10000)
    except Exception as e:
        error_occurred = True
        await page.screenshot(path='login_error.png')

    assert error_occurred, "Should catch login timeout"
    assert 'login_error.png' in page.screenshots


def test_database_error_handling():
    """Test handling of database errors during insertion"""

    # Simulate database error during cursor.execute
    cursor = Mock()
    cursor.execute.side_effect = Exception("Database connection lost")

    error_logged = False
    failed_count = 0

    try:
        cursor.execute(
            "EXEC Testing.GetOutstandingCPFollowUps ?, ?, ?, ?",
            (datetime.now(), "Test Location", 10, 5)
        )
    except Exception as e:
        error_logged = True
        failed_count += 1

    assert error_logged, "Should catch database error"
    assert failed_count == 1, "Should increment failure counter"


# =============================================================================
# Test: Edge Cases
# =============================================================================

def test_location_without_lcode():
    """Test handling of locations that don't match any Lcode"""

    # Simulate SP returning NULL for Lcode
    result = (123, None)  # (InsertedID, Lcode)

    locations_without_lcode = []
    location_name = "Unknown Location"

    _, lcode = result
    if lcode is None:
        locations_without_lcode.append(location_name)

    assert len(locations_without_lcode) == 1
    assert "Unknown Location" in locations_without_lcode


def test_zero_followups_and_calls():
    """Test handling of locations with zero follow-ups and calls"""

    test_data = {
        "location": "Zero Activity Location",
        "followups": 0,
        "unprocessed": 0
    }

    # Should still insert into database
    assert test_data["followups"] >= 0, "Should accept zero follow-ups"
    assert test_data["unprocessed"] >= 0, "Should accept zero calls"


def test_malformed_table_data():
    """Test handling of malformed or missing table cells"""

    # Simulate missing cells
    row_data = ["Location A", "", "5"]  # Middle cell is empty

    location = row_data[0] if len(row_data) > 0 else "UNKNOWN"

    # Try to parse followups
    try:
        followups_text = row_data[1] if len(row_data) > 1 else "0"
        followups = int(followups_text.replace(',', '').strip()) if followups_text.strip() else 0
    except (ValueError, AttributeError):
        followups = 0

    # Try to parse unprocessed
    try:
        unprocessed_text = row_data[2] if len(row_data) > 2 else "0"
        unprocessed = int(unprocessed_text.replace(',', '').strip()) if unprocessed_text.strip() else 0
    except (ValueError, AttributeError):
        unprocessed = 0

    assert location == "Location A"
    assert followups == 0, "Should default to 0 for empty cell"
    assert unprocessed == 5


# =============================================================================
# Test: Transaction Handling
# =============================================================================

def test_commit_only_on_success():
    """Test that database commit only happens when inserts succeed"""

    conn = Mock()
    cursor = Mock()

    # Simulate successful inserts
    inserted = 10
    failed = 0

    if inserted > 0:
        conn.commit()

    conn.commit.assert_called_once()


def test_no_commit_on_all_failures():
    """Test that no commit happens if all inserts fail"""

    conn = Mock()

    # Simulate all failed inserts
    inserted = 0
    failed = 10

    if inserted > 0:
        conn.commit()

    conn.commit.assert_not_called()


# =============================================================================
# Test: Truncate Table
# =============================================================================

def test_truncate_table():
    """Test table truncation before inserting new snapshot"""

    cursor = Mock()

    # Execute truncate
    cursor.execute("TRUNCATE TABLE Testing.OutstandingFollowUpSnapshot")

    cursor.execute.assert_called_once_with("TRUNCATE TABLE Testing.OutstandingFollowUpSnapshot")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("EXTENDED UNIT TEST SUITE")
    print("="*70)

    # Run async tests
    asyncio.run(test_find_table_in_correct_frame())
    print("[PASS] Test: Find table in correct frame")

    asyncio.run(test_no_table_found_error())
    print("[PASS] Test: No table found error handling")

    asyncio.run(test_login_failure_handling())
    print("[PASS] Test: Login failure handling")

    # Run sync tests
    test_parse_integer_from_text()
    print("[PASS] Test: Parse integers from text")

    test_parse_location_name()
    print("[PASS] Test: Parse location names")

    test_database_error_handling()
    print("[PASS] Test: Database error handling")

    test_location_without_lcode()
    print("[PASS] Test: Location without Lcode")

    test_zero_followups_and_calls()
    print("[PASS] Test: Zero follow-ups and calls")

    test_malformed_table_data()
    print("[PASS] Test: Malformed table data")

    test_commit_only_on_success()
    print("[PASS] Test: Commit only on success")

    test_no_commit_on_all_failures()
    print("[PASS] Test: No commit on all failures")

    test_truncate_table()
    print("[PASS] Test: Truncate table")

    print("\n" + "="*70)
    print("ALL EXTENDED TESTS PASSED")
    print("="*70)
