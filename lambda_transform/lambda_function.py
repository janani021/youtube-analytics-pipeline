import json
import os
import boto3
import csv
from io import StringIO
from urllib.parse import unquote_plus

s3 = boto3.client("s3")
S3_BUCKET = os.environ["S3_BUCKET"]


def lambda_handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]

    # Decode S3 key (handles URL-encoding like %3D)
    decoded_key = unquote_plus(key)

    # Only process JSON files
    if not decoded_key.endswith(".json"):
        return {"message": "Not a JSON file, skipping."}

    # Read raw JSON from S3
    obj = s3.get_object(Bucket=bucket, Key=decoded_key)
    raw_data = json.loads(obj["Body"].read().decode("utf-8"))

    # Extract channel info
    channel = raw_data["channel"]
    channel_id = channel["id"]
    channel_title = channel["snippet"]["title"]

    # Extract videos list
    videos = raw_data.get("videos", [])

    # Prepare CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "video_id",
            "video_title",
            "channel_id",
            "channel_title",
            "view_count",
            "like_count",
        ]
    )

    # One row per video
    for video in videos:
        video_id = video["id"]
        video_title = video["snippet"]["title"]
        stats = video.get("statistics", {})

        view_count = int(stats.get("viewCount", 0))
        like_count = int(stats.get("likeCount", 0))

        writer.writerow(
            [
                video_id,
                video_title,
                channel_id,
                channel_title,
                view_count,
                like_count,
            ]
        )

    # Build curated key
    curated_key = decoded_key.replace("raw/", "curated/").replace(".json", ".csv")

    # Upload CSV to S3
    s3.put_object(
        Bucket=bucket,
        Key=curated_key,
        Body=output.getvalue().encode("utf-8"),
    )

    return {"message": "CSV created", "curated_key": curated_key}
