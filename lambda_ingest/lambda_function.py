import os
import json
import boto3
import urllib.request
from urllib.parse import urlencode
from datetime import datetime, timezone

s3 = boto3.client("s3")

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
S3_BUCKET = os.environ["S3_BUCKET"]

BASE_URL = "https://www.googleapis.com/youtube/v3/channels"


def call_youtube_api(channel_id: str) -> dict:
    params = {
        "part": "snippet,statistics,contentDetails",
        "id": channel_id,
        "key": YOUTUBE_API_KEY,
    }

    query_string = urlencode(params)
    url = f"{BASE_URL}?{query_string}"

    # Make HTTP request
    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
        data = json.loads(body)
        return data


def lambda_handler(event, context):

    # Call YouTube API
    channel_data = call_youtube_api(CHANNEL_ID)

    # Build S3 key with timestamp
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s3_key = f"raw/youtube/channel={CHANNEL_ID}/run_ts={run_ts}.json"

    # Upload to S3
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(channel_data).encode("utf-8"),
    )

    # Return success
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "success", "s3_key": s3_key}),
    }
