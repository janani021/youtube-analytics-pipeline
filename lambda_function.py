import os
import json
import boto3
import requests
from datetime import datetime, timezone

s3 = boto3.client("s3")

# Will set the variables in Lambda
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
S3_BUCKET = os.environ["S3_BUCKET"]

BASE_URL = "https://www.googleapis.com/youtube/v3"


def lambda_handler(event, context):
    """
    This Lambda function:
    - Calls the YouTube Data API for a given channel
    - Saves the JSON response into S3 under a raw/ path
    """

    # Call YouTube API to get channel details
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": CHANNEL_ID,
        "key": YOUTUBE_API_KEY,
    }

    response = requests.get(f"{BASE_URL}/channels", params=params)
    response.raise_for_status()  # raises error if API call failed
    channel_data = response.json()

    # Build an S3 key with a timestamp
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s3_key = f"raw/youtube/channel={CHANNEL_ID}/run_ts={run_ts}.json"

    # Upload JSON to S3
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(channel_data).encode("utf-8"),
    )

    # Return a simple success message
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "success", "s3_key": s3_key}),
    }
