# YouTube Analytics Data Pipeline (AWS Lambda + S3)

This is a simple data engineering project that uses AWS Lambda to fetch data from the YouTube Data API and store it in Amazon S3.

# Tech 

- Python
- AWS Lambda
- Amazon S3
- YouTube Data API v3


## Lambda Functions 
1] `lambda_injest/lambda_function.py` (root) – Ingestion Lambda: calls YouTube API and stores raw JSON in S3 under `raw/`.

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