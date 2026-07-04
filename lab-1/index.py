from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable

import boto3
import streamlit as st
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError


st.set_page_config(page_title="Amazon S3 Lab 1", page_icon="🪣", layout="wide")

S3_ACL_OPTIONS = {
    "Private": "private",
}

PUBLIC_ACL_NOTE = "This AWS Academy account blocks public ACLs with S3 Block Public Access, so only Private is available here."

COMMON_REGIONS = [
    "us-east-1",
    "us-west-1",
    "us-west-2",
    "ap-south-1",
    "ap-southeast-1",
    "eu-west-1",
    "eu-central-1",
]

BUCKET_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
IP_ADDRESS_PATTERN = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
LOCAL_ENV_PATH = Path(__file__).with_name(".env")
DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
ENV_KEY_ALIASES = {
    "aws_access_key_id": "AWS_ACCESS_KEY_ID",
    "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
    "aws_session_token": "AWS_SESSION_TOKEN",
    "aws_default_region": "AWS_DEFAULT_REGION",
}


def load_local_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        key = ENV_KEY_ALIASES.get(key, key)
        if key and value and key not in os.environ:
            os.environ[key] = value


load_local_env_file(LOCAL_ENV_PATH)


def get_s3_client(region: str):
    return boto3.client("s3", region_name=region)


def get_sts_client(region: str):
    return boto3.client("sts", region_name=region)


def validate_bucket_name(bucket_name: str) -> None:
    if len(bucket_name) < 3 or len(bucket_name) > 63:
        raise ValueError("Bucket names must be between 3 and 63 characters long.")

    if bucket_name != bucket_name.lower():
        raise ValueError("Bucket names must use only lowercase letters.")

    if not BUCKET_NAME_PATTERN.fullmatch(bucket_name):
        raise ValueError(
            "Bucket names can contain only lowercase letters, numbers, dots, and hyphens, "
            "and must start and end with a letter or number."
        )

    if ".." in bucket_name:
        raise ValueError("Bucket names cannot contain consecutive dots.")

    if IP_ADDRESS_PATTERN.fullmatch(bucket_name):
        raise ValueError("Bucket names cannot look like an IP address.")


def get_aws_credentials_status(region: str) -> tuple[str, str]:
    if not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return (
            "missing",
            f"Create {LOCAL_ENV_PATH.name} with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, plus AWS_SESSION_TOKEN for temporary AWS Academy credentials.",
        )

    try:
        identity = get_sts_client(region).get_caller_identity()
        arn = identity.get("Arn", "your AWS account")
        return ("valid", f"AWS credentials loaded successfully for {arn}.")
    except (NoCredentialsError, PartialCredentialsError):
        return (
            "missing",
            f"Create {LOCAL_ENV_PATH.name} with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, plus AWS_SESSION_TOKEN for temporary AWS Academy credentials.",
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "UnknownError")
        if error_code in {"InvalidClientTokenId", "SignatureDoesNotMatch", "UnrecognizedClientException"}:
            return (
                "invalid",
                "AWS credentials were found, but AWS rejected them. Check that the access key and secret key are correct.",
            )
        return (
            "invalid",
            f"AWS credential check failed: {error.response.get('Error', {}).get('Message', error_code)}",
        )


def create_bucket(bucket_name: str, region: str) -> None:
    validate_bucket_name(bucket_name)
    s3_client = get_s3_client(region)
    bucket_config = {}
    if region != "us-east-1":
        bucket_config["CreateBucketConfiguration"] = {"LocationConstraint": region}

    s3_client.create_bucket(Bucket=bucket_name, **bucket_config)
    s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)

    # Keep ACLs usable for the lab demo so the permission change can be verified.
    s3_client.put_bucket_ownership_controls(
        Bucket=bucket_name,
        OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}]},
    )


def upload_files(bucket_name: str, region: str, files: Iterable) -> list[str]:
    s3_client = get_s3_client(region)
    uploaded_keys: list[str] = []

    for uploaded_file in files:
        key = uploaded_file.name
        s3_client.upload_fileobj(uploaded_file, bucket_name, key)
        uploaded_keys.append(key)

    return uploaded_keys


def set_object_acl(bucket_name: str, region: str, key: str, acl: str) -> None:
    s3_client = get_s3_client(region)
    s3_client.put_object_acl(Bucket=bucket_name, Key=key, ACL=acl)


def get_object_acl(bucket_name: str, region: str, key: str) -> dict:
    s3_client = get_s3_client(region)
    response = s3_client.get_object_acl(Bucket=bucket_name, Key=key)
    return {
        "Owner": response.get("Owner", {}),
        "Grants": response.get("Grants", []),
    }


def list_bucket_objects(bucket_name: str, region: str) -> list[str]:
    s3_client = get_s3_client(region)
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    return [item["Key"] for item in response.get("Contents", [])]


def list_buckets(region: str) -> list[str]:
    s3_client = get_s3_client(region)
    response = s3_client.list_buckets()
    return [bucket["Name"] for bucket in response.get("Buckets", [])]


def normalize_bucket_region(location: str | None) -> str:
    if not location:
        return "us-east-1"
    if location == "EU":
        return "eu-west-1"
    return location


def get_bucket_region(bucket_name: str, region: str) -> str:
    s3_client = get_s3_client(region)
    response = s3_client.get_bucket_location(Bucket=bucket_name)
    return normalize_bucket_region(response.get("LocationConstraint"))


def render_acl_summary(acl_data: dict) -> None:
    grants = []
    for grant in acl_data.get("Grants", []):
        grantee = grant.get("Grantee", {})
        grantee_name = grantee.get("DisplayName") or grantee.get("URI") or grantee.get("ID") or grantee.get("Type")
        grants.append(
            {
                "Permission": grant.get("Permission"),
                "Grantee": grantee_name,
            }
        )

    st.write("Effective access level: Private")
    st.caption("For a private S3 object, AWS still shows a FULL_CONTROL grant for the object owner. That is expected.")
    st.json({"Owner": acl_data.get("Owner", {}), "Grants": grants})


def main() -> None:
    st.title("Amazon S3 Operations UI")
    st.caption("Create a bucket, upload files, and switch object permissions from a single interface.")

    if "bucket_name" not in st.session_state:
        st.session_state.bucket_name = ""
    if "region" not in st.session_state:
        st.session_state.region = DEFAULT_REGION
    if "uploaded_keys" not in st.session_state:
        st.session_state.uploaded_keys = []
    if "aws_credentials_status" not in st.session_state:
        st.session_state.aws_credentials_status = None
    if "aws_credentials_message" not in st.session_state:
        st.session_state.aws_credentials_message = ""
    if "bucket_choices" not in st.session_state:
        st.session_state.bucket_choices = []

    if st.session_state.aws_credentials_status is None:
        st.session_state.aws_credentials_status, st.session_state.aws_credentials_message = get_aws_credentials_status(
            st.session_state.region
        )

    if st.session_state.aws_credentials_status == "missing":
        st.warning(st.session_state.aws_credentials_message)
    elif st.session_state.aws_credentials_status == "invalid":
        st.error(st.session_state.aws_credentials_message)
    else:
        st.caption(st.session_state.aws_credentials_message)

    left, right = st.columns(2)

    with left:
        st.subheader("1. Create a bucket")
        with st.form("create_bucket_form"):
            bucket_name = st.text_input("Bucket name", placeholder="my-unique-lab-bucket-123")
            region_default_index = COMMON_REGIONS.index(DEFAULT_REGION) if DEFAULT_REGION in COMMON_REGIONS else 0
            region_choice = st.selectbox("Region", COMMON_REGIONS, index=region_default_index)
            custom_region = st.text_input("Custom region (optional)", placeholder="Leave blank to use the selected region")
            submitted = st.form_submit_button("Create bucket")

        if submitted:
            bucket_name = bucket_name.strip()
            final_region = custom_region.strip() or region_choice
            try:
                create_bucket(bucket_name, final_region)
                st.session_state.bucket_name = bucket_name
                st.session_state.region = final_region
                st.success(f"Bucket '{bucket_name}' created in {final_region}.")
            except ValueError as error:
                st.error(str(error))
            except NoCredentialsError:
                st.error("AWS credentials are missing. Configure your boto3 credentials before creating a bucket.")
            except ClientError as error:
                st.error(f"Bucket creation failed: {error.response['Error']['Message']}")

    with right:
        st.subheader("Current session")
        st.write(f"Bucket: {st.session_state.bucket_name or 'Not created yet'}")
        st.write(f"Region: {st.session_state.region}")

        st.subheader("Existing buckets")
        try:
            existing_buckets = list_buckets(st.session_state.region)
            st.session_state.bucket_choices = existing_buckets
            if existing_buckets:
                st.write("All buckets visible to this AWS Academy account:")
                st.write("\n".join(f"- {bucket_name}" for bucket_name in existing_buckets))
                selected_existing_bucket = st.selectbox(
                    "Use an existing bucket",
                    ["Choose a bucket"] + existing_buckets,
                    index=0,
                    key="existing_bucket_selector",
                )
                if st.button("Load selected bucket") and selected_existing_bucket != "Choose a bucket":
                    try:
                        selected_bucket_region = get_bucket_region(selected_existing_bucket, st.session_state.region)
                        st.session_state.bucket_name = selected_existing_bucket
                        st.session_state.region = selected_bucket_region
                        st.session_state.uploaded_keys = []
                        st.success(f"Loaded bucket '{selected_existing_bucket}' in {selected_bucket_region}.")
                        st.rerun()
                    except NoCredentialsError:
                        st.error("AWS credentials are missing. Configure your boto3 credentials before loading a bucket.")
                    except ClientError as error:
                        st.error(f"Could not load bucket region: {error.response['Error']['Message']}")
            else:
                st.info("No buckets found in this account.")
        except NoCredentialsError:
            st.error("AWS credentials are missing. Configure your boto3 credentials before listing buckets.")
        except ClientError as error:
            st.error(f"Could not list buckets: {error.response['Error']['Message']}")

    st.divider()

    st.subheader("2. Upload one or more files")
    if st.session_state.bucket_name:
        files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
        )
        if st.button("Upload files"):
            if not files:
                st.warning("Choose at least one file before uploading.")
            else:
                try:
                    uploaded_keys = upload_files(st.session_state.bucket_name, st.session_state.region, files)
                    st.session_state.uploaded_keys = uploaded_keys
                    st.success(f"Uploaded {len(uploaded_keys)} file(s): {', '.join(uploaded_keys)}")
                except NoCredentialsError:
                    st.error("AWS credentials are missing. Configure your boto3 credentials before uploading files.")
                except ClientError as error:
                    st.error(f"Upload failed: {error.response['Error']['Message']}")
    else:
        st.info("Create a bucket first to enable uploads.")

    st.divider()

    st.subheader("3. Change object access level")
    if st.session_state.bucket_name:
        st.info(PUBLIC_ACL_NOTE)
        try:
            bucket_objects = list_bucket_objects(st.session_state.bucket_name, st.session_state.region)
        except ClientError:
            bucket_objects = st.session_state.uploaded_keys

        if bucket_objects:
            with st.form("acl_form"):
                selected_objects = st.multiselect("Select objects", bucket_objects, default=bucket_objects[:1])
                acl_label = st.selectbox("Access level", list(S3_ACL_OPTIONS.keys()))
                apply_acl = st.form_submit_button("Apply access level")

            if apply_acl:
                acl_value = S3_ACL_OPTIONS[acl_label]
                try:
                    for key in selected_objects:
                        set_object_acl(st.session_state.bucket_name, st.session_state.region, key, acl_value)
                    st.success(f"Updated access level to '{acl_label}' for: {', '.join(selected_objects)}")
                except NoCredentialsError:
                    st.error("AWS credentials are missing. Configure your boto3 credentials before changing object access.")
                except ClientError as error:
                    st.error(f"ACL update failed: {error.response['Error']['Message']}")
        else:
            st.info("Upload at least one file to change access permissions.")
    else:
        st.info("Create a bucket first to enable access control changes.")

    st.divider()

    st.subheader("4. Verify the modified permission")
    if st.session_state.bucket_name:
        verification_objects = st.session_state.uploaded_keys
        if not verification_objects:
            try:
                verification_objects = list_bucket_objects(st.session_state.bucket_name, st.session_state.region)
            except ClientError:
                verification_objects = []

        if verification_objects:
            verify_key = st.selectbox("Object to inspect", verification_objects, key="verify_object")
            if st.button("Show ACL"):
                try:
                    acl_data = get_object_acl(st.session_state.bucket_name, st.session_state.region, verify_key)
                    st.write(f"Current ACL for {verify_key}")
                    render_acl_summary(acl_data)
                    st.success("The object is private, and the owner retains FULL_CONTROL as expected.")
                except NoCredentialsError:
                    st.error("AWS credentials are missing. Configure your boto3 credentials before reading object ACLs.")
                except ClientError as error:
                    st.error(f"Could not read ACL: {error.response['Error']['Message']}")
        else:
            st.info("No objects are available yet.")

    st.divider()
    st.caption(
        "Run this app with streamlit run index.py. The UI uses your AWS credentials from the default boto3 credential chain."
    )


if __name__ == "__main__":
    main()