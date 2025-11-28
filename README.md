# YouTube Analytics Data Pipeline (AWS Lambda + S3)

This is a simple data engineering project that uses AWS Lambda to fetch data from the YouTube Data API and store it in Amazon S3.

# What it does

- Calls the YouTube Data API for a specific channel
- Retrieves channel details (snippet, statistics, contentDetails)
- Saves the raw JSON response into an S3 bucket under a `raw/` folder
- Can be triggered manually or on a schedule (via EventBridge)

# Tech 

- Python
- AWS Lambda
- Amazon S3
- YouTube Data API v3

# Environment Variables (set in Lambda, not in code)

- `YOUTUBE_API_KEY` – your YouTube Data API v3 key
- `CHANNEL_ID` – the ID of the YouTube channel you want to track
- `S3_BUCKET` – the name of the S3 bucket where data will be stored
