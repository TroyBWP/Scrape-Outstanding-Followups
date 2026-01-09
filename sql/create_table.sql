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

    -- Create indexes for performance
    CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_dtSnapshot
    ON Testing.OutstandingFollowUpSnapshot(dtSnapshot DESC);

    CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_Lcode
    ON Testing.OutstandingFollowUpSnapshot(Lcode);

    PRINT 'Table and indexes created successfully';
END
ELSE
BEGIN
    PRINT 'Table already exists - no changes made';
END
GO
