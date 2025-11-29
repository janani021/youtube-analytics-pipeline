# YouTube Analytics Data Pipeline (AWS Lambda + S3)

This is a simple data engineering project that uses AWS Lambda to fetch data from the YouTube Data API and store it in Amazon S3.

# Tech 

- Python
- AWS Lambda
- Amazon S3
- YouTube Data API v3


## Lambda Functions 
1] `lambda_injest/lambda_function.py` – Ingestion Lambda: calls YouTube API and stores raw JSON in S3 under `raw/`.

# Environment Variables (set in Lambda, not in code)

- `YOUTUBE_API_KEY` – your YouTube Data API v3 key
- `CHANNEL_ID` – the ID of the YouTube channel you want to track
- `S3_BUCKET` – the name of the S3 bucket where data will be stored

# What it does

- Calls the YouTube Data API for a specific channel
- Retrieves channel details (snippet, statistics, contentDetails)
- Saves the raw JSON response into an S3 bucket under a `raw/` folder
- Can be triggered manually or on a schedule (via EventBridge)

2] `lambda_transform/lambda_function.py` – Transform Lambda: triggered by S3, reads raw JSON and writes a curated CSV under `curated/`.

# Environment Variables (set in Lambda, not in code)
- `S3_BUCKET` – the name of the S3 bucket where data will be stored

# What it does

- Gets automatically triggered by S3 when a new raw JSON file is created under the `raw/` folder
- Decodes the S3 object key (handles URL-encoded characters like `%3D`)
- Reads the raw YouTube channel JSON from S3
- Extracts key fields from the response (channel ID, channel title, subscriber count, view count)
- Converts the extracted data into a CSV file
- Saves the curated CSV into the same S3 bucket under a `curated/` folder

# Snowflake Setup (Storage Integration + Snowpipe)
Snowflake needs permission to read curated CSV files from the S3 bucket.
This requires creating an AWS IAM role and a Snowflake storage integration.
1. Create an IAM Role in AWS
This IAM role allows Snowflake to access your S3 bucket.
Steps in AWS IAM:
Create Role → AWS account → Another AWS account
Name the role: snowflake_yt_s3_role
Attach this inline policy (grants Snowflake read access to the curated folder):
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::yt-analytics-021",
        "arn:aws:s3:::yt-analytics-021/curated/*"
      ]
    }
  ]
}
Leave the trust policy blank for now — Snowflake provides the values next.

2. Create the Snowflake Storage Integration
Run DESC STORAGE INTEGRATION yt_s3_int;
Snowflake returns:
STORAGE_AWS_IAM_USER_ARN
STORAGE_AWS_EXTERNAL_ID
These two must be added to the trust policy.

3. Update IAM Role Trust Policy
In AWS → IAM → Roles → snowflake_yt_s3_role → Trust relationships:
Replace with:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "<STORAGE_AWS_IAM_USER_ARN-from-Snowflake>"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<STORAGE_AWS_EXTERNAL_ID-from-Snowflake>"
        }
      }
    }
  ]
}
This allows Snowflake to assume your role securely.

4. Grant Snowflake Role Access to the Integration
GRANT USAGE ON INTEGRATION yt_s3_int TO ROLE SYSADMIN;
This allows your Snowpipe + stages to actually use the integration.