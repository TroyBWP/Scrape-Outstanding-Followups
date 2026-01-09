-- Create table for Outstanding Follow-Ups snapshots
-- Run this in Operations database

USE Operations;
GO

-- Create table if it doesn't exist (safe for production)
IF OBJECT_ID('Testing.OutstandingFollowUpSnapshot', 'U') IS NULL
BEGIN
    CREATE TABLE Testing.OutstandingFollowUpSnapshot (
        ID INT IDENTITY(1,1) PRIMARY KEY,
        dtSnapshot DATETIME NOT NULL DEFAULT GETDATE(),
        Lcode VARCHAR(10) NULL,
        CallPotential_LocationName VARCHAR(255) NOT NULL,
        UnprocessedFollowUps INT NOT NULL,
        UnprocessedCalls INT NOT NULL
    );
END
ELSE
BEGIN
    -- Add UnprocessedCalls column if it doesn't exist
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                   WHERE TABLE_SCHEMA = 'Testing'
                   AND TABLE_NAME = 'OutstandingFollowUpSnapshot'
                   AND COLUMN_NAME = 'UnprocessedCalls')
    BEGIN
        ALTER TABLE Testing.OutstandingFollowUpSnapshot
        ADD UnprocessedCalls INT NOT NULL DEFAULT 0;
        PRINT 'Added UnprocessedCalls column';
    END
END

IF OBJECT_ID('Testing.OutstandingFollowUpSnapshot', 'U') IS NOT NULL
BEGIN

    -- Create indexes for performance (safe for re-runs)
    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'IX_OutstandingFollowUpSnapshot_dtSnapshot'
                   AND object_id = OBJECT_ID('Testing.OutstandingFollowUpSnapshot'))
    BEGIN
        CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_dtSnapshot
        ON Testing.OutstandingFollowUpSnapshot(dtSnapshot DESC);
        PRINT 'Created dtSnapshot index';
    END

    IF NOT EXISTS (SELECT 1 FROM sys.indexes
                   WHERE name = 'IX_OutstandingFollowUpSnapshot_Lcode'
                   AND object_id = OBJECT_ID('Testing.OutstandingFollowUpSnapshot'))
    BEGIN
        CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_Lcode
        ON Testing.OutstandingFollowUpSnapshot(Lcode);
        PRINT 'Created Lcode index';
    END

    PRINT 'Table and indexes ready';
END
ELSE
BEGIN
    PRINT 'Table already exists - no changes made';
END
GO
