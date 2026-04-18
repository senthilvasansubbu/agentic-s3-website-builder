"""
Hosting service — deploys a completed website to AWS S3 static hosting
or saves it locally.  Supports per-website custom domain configuration notes.
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, List

import boto3
from botocore.exceptions import ClientError


def _get_s3_client(access_key: str, secret_key: str, region: str):
    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def deploy_to_s3(
    local_dir: str,
    bucket_name: str,
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    prefix: str = "",
) -> Optional[str]:
    """
    Upload every file in local_dir to S3 bucket under optional prefix.
    Configures the bucket for static website hosting.
    Returns the website URL or None on failure.
    """
    client = _get_s3_client(access_key, secret_key, region)
    try:
        # Enable static website hosting
        client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration={
                "IndexDocument": {"Suffix": "index.html"},
                "ErrorDocument": {"Key": "404.html"},
            },
        )
        # Allow public read
        client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=f"""{{
              "Version":"2012-10-17",
              "Statement":[{{
                "Sid":"PublicReadGetObject",
                "Effect":"Allow",
                "Principal":"*",
                "Action":"s3:GetObject",
                "Resource":"arn:aws:s3:::{bucket_name}/*"
              }}]
            }}""",
        )
        # Upload files
        uploaded: List[str] = []
        for path in Path(local_dir).rglob("*"):
            if path.is_file():
                key = (f"{prefix}/{path.relative_to(local_dir)}" if prefix else str(path.relative_to(local_dir))).replace("\\", "/")
                content_type, _ = mimetypes.guess_type(str(path))
                client.upload_file(
                    str(path),
                    bucket_name,
                    key,
                    ExtraArgs={"ContentType": content_type or "application/octet-stream"},
                )
                uploaded.append(key)
        print(f"✅ Deployed {len(uploaded)} files to s3://{bucket_name}/{prefix}")
        return f"http://{bucket_name}.s3-website-{region}.amazonaws.com/{prefix}"
    except ClientError as exc:
        print(f"[hosting] S3 deploy error: {exc}")
        return None


def save_locally(html_content: str, output_dir: str, filename: str) -> str:
    """Write HTML to disk and return the full path."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filepath


def custom_domain_instructions(domain: str, bucket_name: str, region: str) -> str:
    """Return human-readable DNS setup instructions for a custom domain."""
    return f"""
To use your custom domain '{domain}' with your S3-hosted website:

1. In your DNS provider, create a CNAME record:
   Name:  {domain}
   Value: {bucket_name}.s3-website-{region}.amazonaws.com

2. (Optional) For HTTPS, set up AWS CloudFront in front of the S3 bucket
   and request an ACM certificate for '{domain}'.

3. Update WEBSITE_DOMAIN in your .env to '{domain}'.
"""
