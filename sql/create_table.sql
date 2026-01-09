-- Create table for Outstanding Follow-Ups snapshots
-- Run this in Operations database

USE Operations;
GO

IF OBJECT_ID('Testing.OutstandingFollowUpSnapshot', 'U') IS NOT NULL
    DROP TABLE Testing.OutstandingFollowUpSnapshot;
GO

CREATE TABLE Testing.OutstandingFollowUpSnapshot (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    dtSnapshot DATETIME NOT NULL DEFAULT GETDATE(),
    Lcode VARCHAR(10) NULL,
    CallPotential_LocationName VARCHAR(255) NOT NULL,
    UnprocessedFollowUps INT NOT NULL,
    UnprocessedCalls INT NOT NULL
);
GO

-- Create index for performance
CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_dtSnapshot
ON Testing.OutstandingFollowUpSnapshot(dtSnapshot DESC);
GO

CREATE NONCLUSTERED INDEX IX_OutstandingFollowUpSnapshot_Lcode
ON Testing.OutstandingFollowUpSnapshot(Lcode);
GO
