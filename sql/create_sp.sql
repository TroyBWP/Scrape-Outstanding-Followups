-- Create stored procedure to insert Outstanding Follow-Up snapshots
-- Run this in Operations database

USE Operations;
GO

IF OBJECT_ID('Testing.GetOutstandingCPFollowUps', 'P') IS NOT NULL
    DROP PROCEDURE Testing.GetOutstandingCPFollowUps;
GO

CREATE PROCEDURE Testing.GetOutstandingCPFollowUps
    @dtSnapshot DATETIME,
    @CallPotential_LocationName VARCHAR(255),
    @UnprocessedFollowUps INT,
    @UnprocessedCalls INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @Lcode VARCHAR(10);

    -- Lookup Lcode from location name
    SELECT TOP 1 @Lcode = ld.Lcode
    FROM Connectors.CallPotential.locations_hist lh
    LEFT OUTER JOIN Operations.dbo.Westport_LocationData ld
        ON ld.CallPotentialLocationID = lh.old_location_id
        OR ld.CallPotentialLocationID = lh.new_location_id
    WHERE lh.location_name = @CallPotential_LocationName
        AND ld.DateEnd IS NULL
    ORDER BY lh.location_id DESC; -- Most recent location_id if multiple matches

    -- Insert the snapshot
    INSERT INTO Testing.OutstandingFollowUpSnapshot (
        dtSnapshot,
        Lcode,
        CallPotential_LocationName,
        UnprocessedFollowUps,
        UnprocessedCalls
    )
    VALUES (
        @dtSnapshot,
        @Lcode,
        @CallPotential_LocationName,
        @UnprocessedFollowUps,
        @UnprocessedCalls
    );

    -- Return the inserted ID
    SELECT SCOPE_IDENTITY() AS InsertedID, @Lcode AS Lcode;
END;
GO

-- Grant EXECUTE permission to TroyAI
GRANT EXECUTE ON Testing.GetOutstandingCPFollowUps TO TroyAI;
GO

PRINT 'Stored procedure created successfully';
GO
