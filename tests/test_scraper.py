"""
Unit tests for CallPotential Outstanding Follow-Ups scraper
Tests credential retrieval, database connection, and scraping logic
"""

import asyncio
import pyodbc
import keyring
from datetime import datetime
from scrape_followups import CallPotentialScraper


def test_credentials():
    """Test that credentials can be retrieved from keyring"""
    print("\n" + "="*60)
    print("TEST 1: Credential Retrieval")
    print("="*60)

    username = keyring.get_password('CallPotential', 'Username')
    password = keyring.get_password('CallPotential', 'Password')

    assert username is not None, "Username not found in keyring"
    assert password is not None, "Password not found in keyring"

    print(f"[PASS] Username retrieved: {username[:3]}***")
    print("[PASS] Password retrieved: [hidden]")
    print("PASS: Credentials successfully retrieved")


def test_database_connection():
    """Test database connection and stored procedure exists"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection & Stored Procedure")
    print("="*60)

    password = keyring.get_password('AIDevSQLDatabase', 'TroyAI')
    assert password is not None, "Database password not found in keyring"

    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER=wpicsql01.westport.dom;'
        f'DATABASE=Operations;'
        f'UID=TroyAI;'
        f'PWD={password}'
    )

    conn = pyodbc.connect(conn_str)
    print("[OK] Database connection established")

    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("""
        SELECT OBJECT_ID('Testing.OutstandingFollowUpSnapshot', 'U')
    """)
    table_exists = cursor.fetchone()[0]
    assert table_exists is not None, "Table Testing.OutstandingFollowUpSnapshot does not exist"
    print("[OK] Table Testing.OutstandingFollowUpSnapshot exists")

    # Check if stored procedure exists
    cursor.execute("""
        SELECT OBJECT_ID('Testing.GetOutstandingCPFollowUps', 'P')
    """)
    sp_exists = cursor.fetchone()[0]
    assert sp_exists is not None, "Stored procedure Testing.GetOutstandingCPFollowUps does not exist"
    print("[OK] Stored procedure Testing.GetOutstandingCPFollowUps exists")

    # Verify table schema
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'Testing'
        AND TABLE_NAME = 'OutstandingFollowUpSnapshot'
        ORDER BY ORDINAL_POSITION
    """)

    columns = cursor.fetchall()
    expected_columns = {
        'ID': 'int',
        'dtSnapshot': 'datetime',
        'Lcode': 'varchar',
        'CallPotential_LocationName': 'varchar',
        'UnprocessedFollowUps': 'int',
        'UnprocessedCalls': 'int'
    }

    for col in columns:
        col_name = col[0]
        col_type = col[1]
        if col_name in expected_columns:
            assert expected_columns[col_name] == col_type, f"Column {col_name} has wrong type: {col_type}"
            print(f"[OK] Column {col_name} ({col_type}) validated")

    cursor.close()
    conn.close()
    print("PASS: Database schema validated")


def test_stored_procedure_execution():
    """Test stored procedure can be called successfully"""
    print("\n" + "="*60)
    print("TEST 3: Stored Procedure Execution")
    print("="*60)

    password = keyring.get_password('AIDevSQLDatabase', 'TroyAI')
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER=wpicsql01.westport.dom;'
        f'DATABASE=Operations;'
        f'UID=TroyAI;'
        f'PWD={password}'
    )

    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    try:
        # Test insert (truncate is now handled separately in the scraper)
        test_time = datetime.now()
        test_location = "TEST_LOCATION_UNIT_TEST"

        cursor.execute(
            "EXEC Testing.GetOutstandingCPFollowUps ?, ?, ?, ?",
            (test_time, test_location, 10, 5)
        )

        result = cursor.fetchone()
        assert result is not None, "Stored procedure did not return result"

        inserted_id = result[0]
        lcode = result[1]

        print(f"[OK] Stored procedure executed successfully")
        print(f"[OK] Inserted ID: {inserted_id}")
        print(f"[OK] Lcode: {lcode if lcode else 'NULL (expected for test location)'}")

        conn.commit()

        # Verify data was inserted
        cursor.execute("""
            SELECT TOP 1 *
            FROM Testing.OutstandingFollowUpSnapshot
            WHERE CallPotential_LocationName = ?
            ORDER BY ID DESC
        """, (test_location,))

        row = cursor.fetchone()
        assert row is not None, "Test record not found in database"
        assert row[4] == 10, f"UnprocessedFollowUps mismatch: expected 10, got {row[4]}"
        assert row[5] == 5, f"UnprocessedCalls mismatch: expected 5, got {row[5]}"

        print("[OK] Data verified in database")
        print(f"  UnprocessedFollowUps: {row[4]}")
        print(f"  UnprocessedCalls: {row[5]}")

    finally:
        # Clean up test data (runs even if test fails)
        try:
            cursor.execute("DELETE FROM Testing.OutstandingFollowUpSnapshot WHERE CallPotential_LocationName = ?", (test_location,))
            conn.commit()
            print("[OK] Test data cleaned up")
        except Exception as cleanup_error:
            print(f"[WARN] Cleanup failed: {cleanup_error}")

        cursor.close()
        conn.close()

    print("PASS: Stored procedure execution validated")


async def test_scraper_initialization():
    """Test scraper class initialization"""
    print("\n" + "="*60)
    print("TEST 4: Scraper Initialization")
    print("="*60)

    scraper = CallPotentialScraper()

    assert scraper.url == "https://sys.callpotential.com/ui/v2/dashboard", "URL mismatch"
    print(f"[OK] URL configured: {scraper.url}")

    # Test credential retrieval
    scraper._get_credentials()
    assert scraper.username is not None, "Username not retrieved"
    assert scraper.password is not None, "Password not retrieved"
    print(f"[OK] Credentials loaded: {scraper.username[:3]}***")

    # Test database connection
    scraper._get_db_connection()
    assert scraper.db_connection is not None, "Database connection failed"
    print("[OK] Database connection established")

    scraper.db_connection.close()
    print("PASS: Scraper initialization validated")


def run_all_tests():
    """Run all unit tests"""
    print("\n" + "="*70)
    print("CALLPOTENTIAL SCRAPER - UNIT TEST SUITE")
    print("="*70)

    tests = [
        ("Credential Retrieval", test_credentials),
        ("Database Connection & Schema", test_database_connection),
        ("Stored Procedure Execution", test_stored_procedure_execution),
        ("Scraper Initialization", lambda: asyncio.run(test_scraper_initialization()))
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n[FAIL] FAIL: {test_name}")
            print(f"  Error: {e}")
            failed += 1

    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n[OK] ALL TESTS PASSED - Ready for production!")
    else:
        print(f"\n[FAIL] {failed} TEST(S) FAILED - Please review errors above")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
