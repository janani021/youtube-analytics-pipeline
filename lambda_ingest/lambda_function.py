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

BASE_URL = "https://www.googleapis.com/youtube/v3"


def youtube_api_get(path: str, params: dict) -> dict:
    """Helper to call YouTube Data API v3 using urllib."""
    params_with_key = {**params, "key": YOUTUBE_API_KEY}
    query_string = urlencode(params_with_key)
    url = f"{BASE_URL}/{path}?{query_string}"

    with urllib.request.urlopen(url) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def lambda_handler(event, context):
    #  Get channel details (snippet, statistics, contentDetails)
    channel_resp = youtube_api_get(
        "channels",
        {
            "part": "snippet,statistics,contentDetails",
            "id": CHANNEL_ID,
        },
    )

    if not channel_resp.get("items"):
        raise ValueError("No channel data returned from YouTube API")

    channel_item = channel_resp["items"][0]

    # Get uploads playlist ID
    uploads_playlist_id = channel_item["contentDetails"]["relatedPlaylists"]["uploads"]

    #  Get latest videos from uploads playlist (up to 50)
    playlist_resp = youtube_api_get(
        "playlistItems",
        {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
        },
    )

    video_ids = [
        item["contentDetails"]["videoId"]
        for item in playlist_resp.get("items", [])
    ]

    videos_items = []

    if video_ids:
        # Get video details + statistics for those video_ids
        videos_resp = youtube_api_get(
            "videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(video_ids),
            },
        )
        videos_items = videos_resp.get("items", [])

    # Build payload: one channel + many videos
    payload = {
        "channel": channel_item,
        "videos": videos_items,
    }

    # Write JSON to S3 (raw zone)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s3_key = f"raw/youtube/channel={CHANNEL_ID}/run_ts={run_ts}.json"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(payload).encode("utf-8"),
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "success", "s3_key": s3_key}),
    }
