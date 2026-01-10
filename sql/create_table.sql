-- Create table for Outstanding Follow-Ups snapshots
-- Run this in Operations database

USE Operations;
GO

-- Create Testing schema if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Testing')
BEGIN
    EXEC('CREATE SCHEMA Testing');
    PRINT 'Created Testing schema';
END
GO

-- Drop and recreate table for clean schema
IF OBJECT_ID('Testing.OutstandingFollowUpSnapshot', 'U') IS NOT NULL
BEGIN
    DROP TABLE Testing.OutstandingFollowUpSnapshot;
    PRINT 'Dropped existing table';
END

CREATE TABLE Testing.OutstandingFollowUpSnapshot (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    dtSnapshot DATETIME NOT NULL DEFAULT GETDATE(),
    Region VARCHAR(50) NULL,
    District_Manager VARCHAR(100) NULL,
    Lcode VARCHAR(10) NULL,
    Location VARCHAR(255) NOT NULL,
    Unproc_FollowUps INT NOT NULL,
    Unproc_Calls INT NOT NULL
);

-- Create indexes for performance
CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_dtSnapshot
ON Testing.OutstandingFollowUpSnapshot(dtSnapshot DESC);

PRINT 'Table created successfully';

-- Grant table permissions to TroyAI (since we removed EXECUTE AS)
GRANT SELECT, INSERT, UPDATE, DELETE ON Testing.OutstandingFollowUpSnapshot TO TroyAI;
PRINT 'Granted table permissions to TroyAI';
GO
