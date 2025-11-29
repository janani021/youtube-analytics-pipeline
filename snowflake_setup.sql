
/********************************************************************************************
 1) SET ROLE
   SYSADMIN is used to create DB objects.
********************************************************************************************/
USE ROLE SYSADMIN;

/********************************************************************************************
 2) CREATE DATABASE + SCHEMA
   Stores curated data loaded from S3.
********************************************************************************************/
CREATE OR REPLACE DATABASE YOUTUBE_DB;
CREATE OR REPLACE SCHEMA YOUTUBE_DB.CURATED;

USE DATABASE YOUTUBE_DB;
USE SCHEMA CURATED;

/********************************************************************************************
 3) CREATE FILE FORMAT 
   Defines how Snowflake should read the CSV files in S3.
********************************************************************************************/
CREATE OR REPLACE FILE FORMAT CSV_FORMAT_YT
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"';

/********************************************************************************************
 4) CREATE STORAGE INTEGRATION
   Must be done as ACCOUNTADMIN because it is an account-level object.
   Allows Snowflake to assume an AWS IAM role and read from S3.
   In AWS IAM, you should have (or create) a role like snowflake-yt-s3-role 
********************************************************************************************/
USE ROLE ACCOUNTADMIN;

CREATE OR REPLACE STORAGE INTEGRATION yt_s3_int
  TYPE = EXTERNAL_STAGE
  STORAGE_PROVIDER = S3
  ENABLED = TRUE
  STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::000345487561:role/snowflake_yt_s3_role'
  STORAGE_ALLOWED_LOCATIONS = ('s3://yt-analytics-021/curated/');

-- Shows the IAM user ARN + External ID needed in AWS trust policy
DESC STORAGE INTEGRATION yt_s3_int;

/********************************************************************************************
 5) CREATE EXTERNAL STAGE
   A pointer to your S3 bucket & path.
   Snowflake uses this stage to read incoming CSVs.
********************************************************************************************/
USE ROLE SYSADMIN;
USE DATABASE YOUTUBE_DB;
USE SCHEMA CURATED;

CREATE OR REPLACE STAGE yt_curated_stage
  URL = 's3://yt-analytics-021/curated/'
  STORAGE_INTEGRATION = yt_s3_int
  FILE_FORMAT = CSV_FORMAT_YT;

-- See files in the S3 bucket through Snowflake
LIST @yt_curated_stage;

/********************************************************************************************
 6) CREATE CURATED ANALYTICS TABLE
   Stores daily YouTube stats from uploaded CSVs.
********************************************************************************************/
CREATE OR REPLACE TABLE yt_video_daily_stats (
  video_id        STRING,
  video_title     STRING,
  channel_id      STRING,
  channel_title   STRING,
  view_count      NUMBER,
  like_count      NUMBER,
  snapshot_date   DATE DEFAULT CURRENT_DATE()  -- tracks the load date
);

/********************************************************************************************
 7) INITIAL MANUAL LOAD (OPTIONAL)
   Useful the first time before Snowpipe is configured.
********************************************************************************************/
COPY INTO yt_video_daily_stats
FROM (
  SELECT
    $1::STRING       AS video_id,
    $2::STRING       AS video_title,
    $3::STRING       AS channel_id,
    $4::STRING       AS channel_title,
    $5::NUMBER       AS view_count,
    $6::NUMBER       AS like_count,
    CURRENT_DATE()   AS snapshot_date
  FROM @yt_curated_stage
)
FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT_YT)
ON_ERROR = 'CONTINUE';

SELECT * FROM yt_video_daily_stats LIMIT 20;

/********************************************************************************************
 8) CREATE SNOWPIPE
   Auto-ingests NEW files uploaded to S3.
   S3 event notifications → SQS → Snowpipe → Table
********************************************************************************************/
CREATE OR REPLACE PIPE yt_video_daily_pipe
  AUTO_INGEST = TRUE
  AS
  COPY INTO yt_video_daily_stats
  FROM (
    SELECT
      $1::STRING       AS video_id,
      $2::STRING       AS video_title,
      $3::STRING       AS channel_id,
      $4::STRING       AS channel_title,
      $5::NUMBER       AS view_count,
      $6::NUMBER       AS like_count,
      CURRENT_DATE()   AS snapshot_date
    FROM @yt_curated_stage
  )
  FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT_YT)
  ON_ERROR = 'CONTINUE';

DESC PIPE yt_video_daily_pipe;

/********************************************************************************************
 9) GRANT PERMISSIONS ON INTEGRATION
   Snowpipe needs USAGE permission on the storage integration.
********************************************************************************************/
USE ROLE ACCOUNTADMIN;

SHOW INTEGRATIONS LIKE 'YT_S3_INT';
SHOW GRANTS ON INTEGRATION YT_S3_INT;

-- Allow SYSADMIN (pipe owner) to use the integration
GRANT USAGE ON INTEGRATION YT_S3_INT TO ROLE SYSADMIN;

-- Also allow ACCOUNTADMIN for admin purposes
GRANT USAGE ON INTEGRATION YT_S3_INT TO ROLE ACCOUNTADMIN;

SHOW GRANTS ON INTEGRATION YT_S3_INT;

/********************************************************************************************
 10) PIPE STATUS + BACKFILL
   REFRESH forces the pipeline to re-check S3 for any missed files.
********************************************************************************************/
USE DATABASE YOUTUBE_DB;
USE SCHEMA CURATED;

SHOW PIPES LIKE 'YT_VIDEO_DAILY_PIPE';
-- Requeue any unprocessed S3 files
ALTER PIPE YT_VIDEO_DAILY_PIPE REFRESH;
-- Check status: shows last ingested file, timestamps, SQS status, etc.
SELECT SYSTEM$PIPE_STATUS('YOUTUBE_DB.CURATED.YT_VIDEO_DAILY_PIPE');

/********************************************************************************************
 11) COPY HISTORY (what files were loaded)
********************************************************************************************/
SELECT *
FROM TABLE(
  INFORMATION_SCHEMA.COPY_HISTORY(
    TABLE_NAME => 'YOUTUBE_DB.CURATED.YT_VIDEO_DAILY_STATS',
    START_TIME => DATEADD(day, -1, CURRENT_TIMESTAMP())
  )
)
ORDER BY LAST_LOAD_TIME DESC;

/********************************************************************************************
 12) CHECK FINAL DATA IN THE TABLE
********************************************************************************************/
SELECT
  SNAPSHOT_DATE,
  VIDEO_ID,
  VIDEO_TITLE,
  CHANNEL_TITLE,
  VIEW_COUNT,
  LIKE_COUNT
FROM YOUTUBE_DB.CURATED.YT_VIDEO_DAILY_STATS
ORDER BY SNAPSHOT_DATE DESC
LIMIT 20;