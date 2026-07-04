import boto3
import sys

BUCKET_NAME = "2547119-bucket"


def list_bucket_objects():
    # Create AWS session
    aws_session = boto3.Session()

    # Check whether AWS credentials are configured
    if not aws_session.get_credentials():
        print("AWS credentials not found.")
        print("Run 'aws configure' to set up your credentials.")
        sys.exit(1)

    s3 = aws_session.client("s3")

    print(f"\nListing objects in bucket: {BUCKET_NAME}\n")

    try:
        paginator = s3.get_paginator("list_objects_v2")
        response = paginator.paginate(Bucket=BUCKET_NAME)

        total_files = 0

        print("=" * 90)
        print(f"{'File Name':<45} {'Size(Bytes)':<15} {'Last Modified'}")
        print("=" * 90)

        for page in response:
            if "Contents" not in page:
                continue

            for item in page["Contents"]:
                total_files += 1

                print(
                    f"{item['Key']:<45} "
                    f"{item['Size']:<15} "
                    f"{item['LastModified'].strftime('%Y-%m-%d %H:%M:%S')}"
                )

        print("=" * 90)

        if total_files == 0:
            print("Bucket is empty.")
        else:
            print(f"Total Objects: {total_files}")

        print("\nOperation completed successfully.")
        print("Student Number: 2547119")

    except s3.exceptions.NoSuchBucket:
        print(f"Bucket '{BUCKET_NAME}' does not exist.")

    except Exception as err:
        print(f"Error: {err}")


def main():
    list_bucket_objects()


if __name__ == "__main__":
    main()