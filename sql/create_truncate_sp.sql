-- Create stored procedure to truncate Outstanding Follow-Up snapshots
-- This is called ONCE before inserting new snapshots
-- Run this in Operations database

USE Operations;
GO

IF OBJECT_ID('Testing.TruncateOutstandingFollowUpSnapshot', 'P') IS NOT NULL
    DROP PROCEDURE Testing.TruncateOutstandingFollowUpSnapshot;
GO

CREATE PROCEDURE Testing.TruncateOutstandingFollowUpSnapshot
AS
BEGIN
    SET NOCOUNT ON;

    TRUNCATE TABLE Testing.OutstandingFollowUpSnapshot;
END;
GO

-- Grant EXECUTE permission to TroyAI
GRANT EXECUTE ON Testing.TruncateOutstandingFollowUpSnapshot TO TroyAI;
GO

PRINT 'Truncate stored procedure created successfully';
GO

-- Create stored procedure to delete test records (for unit tests)
IF OBJECT_ID('Testing.DeleteTestFollowUpRecords', 'P') IS NOT NULL
    DROP PROCEDURE Testing.DeleteTestFollowUpRecords;
GO

CREATE PROCEDURE Testing.DeleteTestFollowUpRecords
    @CallPotential_LocationName VARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;

    DELETE FROM Testing.OutstandingFollowUpSnapshot
    WHERE CallPotential_LocationName = @CallPotential_LocationName;
END;
GO

-- Grant EXECUTE permission to TroyAI
GRANT EXECUTE ON Testing.DeleteTestFollowUpRecords TO TroyAI;
GO

PRINT 'Delete test records stored procedure created successfully';
GO
