import re

import boto3
from botocore.exceptions import ClientError

from camera_traps.errors import StorageException


class S3Storage:
    """S3-compatible storage client (works with SeaweedFS, AWS S3, etc.)."""

    def __init__(self, **kwargs):
        self.s3 = boto3.client("s3", **kwargs)

    def init_storage(self, buckets: list[str], folders: list[str] | None = None) -> None:
        """Ensure required S3 buckets exist at startup"""

        for bucket in buckets:
            try:
                self.s3.create_bucket(Bucket=bucket)
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                    raise

        if folders and buckets:
            main_bucket = buckets[0]
            for folder in folders:
                folder_key = f"{folder.strip('/')}/"
                try:
                    self.s3.head_object(Bucket=main_bucket, Key=folder_key)
                except ClientError:
                    self.s3.put_object(Bucket=main_bucket, Key=folder_key, Body=b"")

    def upload(self, key: str, data: bytes, content_type: str, bucket: str | None = None) -> str:
        """Upload bytes to S3 bucket"""

        try:
            self.s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
            return f"s3://{bucket}/{key}"
        except ClientError as e:
            raise StorageException(f"Error uploading {key} to {bucket}: {e}") from e

    def download(self, file_uri: str) -> bytes:
        """Download file bytes from S3 URI"""

        match = re.match(pattern=r"s3://([^/]+)/(.*)", string=file_uri)
        if not match:
            raise StorageException(f"Invalid S3 URI format: {file_uri}")

        bucket, key = match.groups()

        try:
            response = self.s3.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            raise StorageException(f"Error downloading {file_uri}: {e}") from e
