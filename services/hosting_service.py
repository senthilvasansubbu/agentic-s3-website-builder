"""
Hosting service — deploys a completed website to AWS S3 static hosting
or saves it locally.  Supports per-website custom domain configuration notes.
"""
import os
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any

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


def deploy_directory_to_gdrive(
    local_dir: str,
    parent_folder_id: str,
    site_folder_name: str,
    service_account_file: str = "",
    oauth_token: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Upload an entire built website directory to Google Drive preserving folder
    structure. Returns deploy metadata dict or None on failure.

    Authentication (one of):
    - service_account_file: path to a service account JSON key file
    - oauth_token: a short-lived OAuth2 access token (e.g. from OAuth Playground)
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except Exception as exc:
        print(f"[hosting] Google API libraries missing: {exc}")
        return None

    if oauth_token:
        from google.oauth2.credentials import Credentials
        import datetime
        # Set a far-future expiry so the library does NOT attempt a refresh
        # (short-lived tokens from OAuth Playground have no refresh token)
        creds = Credentials(
            token=oauth_token,
            expiry=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        )
    elif service_account_file:
        if not os.path.exists(service_account_file):
            print("[hosting] Google Drive service account file not found")
            return None
        from google.oauth2 import service_account
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
    else:
        print("[hosting] No Google Drive credentials provided (need service_account_file or oauth_token)")
        return None

    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _create_folder(name: str, parent_id: str) -> Optional[str]:
        # Check if folder already exists with this name under parent
        query = f"name='{name.replace("'", "\\'")}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
        results = drive.files().list(q=query, fields="files(id,name)").execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = drive.files().create(body=body, fields="id").execute()
        return folder.get("id")

    try:
        root_folder_id = _create_folder(site_folder_name, parent_folder_id)
        if not root_folder_id:
            return None

        # Make the root folder readable so users can access uploaded files.
        drive.permissions().create(
            fileId=root_folder_id,
            body={"role": "reader", "type": "anyone"},
            fields="id",
        ).execute()

        folder_cache = {"": root_folder_id}

        uploaded_files = 0
        for file_path in Path(local_dir).rglob("*"):
            if not file_path.is_file():
                continue

            rel = file_path.relative_to(local_dir)
            rel_parent = str(rel.parent).replace("\\", "/")
            # Normalize: always use no leading/trailing slash, forward slashes
            norm_rel_parent = rel_parent.strip("/")

            # Build nested folder tree in Drive as needed.
            if norm_rel_parent and norm_rel_parent not in folder_cache:
                parts = norm_rel_parent.split("/")
                cur_path = ""
                cur_parent_id = root_folder_id
                for part in parts:
                    cur_path = f"{cur_path}/{part}" if cur_path else part
                    if cur_path not in folder_cache:
                        new_id = _create_folder(part, cur_parent_id)
                        if not new_id:
                            raise RuntimeError(f"Failed to create Drive folder: {cur_path}")
                        folder_cache[cur_path] = new_id
                    cur_parent_id = folder_cache[cur_path]

            # Use normalized rel_parent for lookup, default to root
            parent_id = folder_cache.get(norm_rel_parent, root_folder_id)
            ctype, _ = mimetypes.guess_type(str(file_path))
            media = MediaFileUpload(str(file_path), mimetype=ctype or "application/octet-stream", resumable=False)
            drive.files().create(
                body={"name": file_path.name, "parents": [parent_id]},
                media_body=media,
                fields="id",
            ).execute()
            uploaded_files += 1

        print(f"✅ Uploaded website directory to Google Drive folder: {root_folder_id}")
        return {
            "url": f"https://drive.google.com/drive/folders/{root_folder_id}",
            "folder_id": root_folder_id,
            "folder_name": site_folder_name,
            "files_uploaded": uploaded_files,
        }
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "invalid_grant" in msg or "Token has been expired" in msg or "credentials do not contain" in msg.lower():
            raise RuntimeError("Google OAuth token has expired. Go to Storage Settings and paste a fresh access token from https://developers.google.com/oauthplayground/")
        print(f"[hosting] Google Drive deploy error: {exc}")
        raise
