import boto3
from botocore.exceptions import ClientError

BUCKET_NAME = "2547119-bucket"

def list_s3_objects():
    # Initialize the S3 client
    s3 = boto3.client('s3')
    
    print(f"Retrieving objects from S3 bucket: '{BUCKET_NAME}'...\n")
    
    try:
        # Call S3 to list objects
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        
        # Check if the bucket has contents
        if 'Contents' in response:
            print(f"{'Key':<35} | {'Size (Bytes)':<12} | {'Last Modified':<30}")
            print("-" * 85)
            for obj in response['Contents']:
                key = obj['Key']
                size = obj['Size']
                last_modified = str(obj['LastModified'])
                print(f"{key:<35} | {size:<12} | {last_modified:<30}")
            print("-" * 85)
            print("\nSuccessfully listed all objects in the bucket.")
        else:
            print("The bucket is empty or contains no objects.")
            print("\nSuccess: Check completed (no objects found).")
            
    except ClientError as e:
        print(f"Error accessing S3 bucket: {e}")
        print("Please ensure your AWS credentials are valid and you have access permissions.")

if __name__ == "__main__":
    list_s3_objects()
