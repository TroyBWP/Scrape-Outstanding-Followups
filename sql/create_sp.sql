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

    DECLARE @LocationName VARCHAR(255);
    DECLARE @Region VARCHAR(50);
    DECLARE @District_Manager VARCHAR(100);
    DECLARE @Lcode VARCHAR(10);

    -- Lookup Location, Region, District Manager, and Lcode from CallPotential location name
    SELECT TOP 1
        @LocationName = ld.Location,
        @Region = UPPER(LEFT(ld.Region, 1)) + LOWER(SUBSTRING(ld.Region, 2, LEN(ld.Region))),
        @District_Manager = dms.LongName,
        @Lcode = ld.Lcode
    FROM Connectors.CallPotential.locations_hist lh
    LEFT OUTER JOIN Operations.dbo.Westport_LocationData ld
        ON (ld.CallPotentialLocationID = lh.old_location_id
            OR ld.CallPotentialLocationID = lh.new_location_id)
        AND ld.DateEnd IS NULL
    LEFT OUTER JOIN Operations.dbo.Westport_DMs dms
        ON dms.DMID = ld.DMID
    WHERE lh.location_name = @CallPotential_LocationName
    ORDER BY ld.Lcode;

    -- Insert the snapshot using ld.Location instead of lh.location_name
    INSERT INTO Operations.Testing.OutstandingFollowUpSnapshot (
        dtSnapshot,
        Region,
        District_Manager,
        Lcode,
        Location,
        Unproc_FollowUps,
        Unproc_Calls
    )
    VALUES (
        @dtSnapshot,
        @Region,
        @District_Manager,
        @Lcode,
        ISNULL(@LocationName, @CallPotential_LocationName), -- Use ld.Location if found, fallback to CallPotential name
        @UnprocessedFollowUps,
        @UnprocessedCalls
    );

    -- Return the inserted ID and Lcode
    SELECT SCOPE_IDENTITY() AS InsertedID, @Lcode AS Lcode;
END;
GO

-- Grant EXECUTE permission to TroyAI
GRANT EXECUTE ON Testing.GetOutstandingCPFollowUps TO TroyAI;
GO

PRINT 'Stored procedure created successfully';
GO
