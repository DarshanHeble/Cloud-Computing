import boto3
from botocore.exceptions import ClientError
from datetime import datetime

BUCKET_NAME = "2547119-bucket"

def generate_inventory_report():
    print("=" * 60)
    print("       AWS RESOURCE INVENTORY REPORT GENERATOR         ")
    print("=" * 60)
    
    report_lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report_lines.append("=" * 80)
    report_lines.append(f"AWS Resource Inventory Report - Generated on {timestamp}")
    report_lines.append(f"Student Register Number: 2547119")
    report_lines.append("=" * 80)
    report_lines.append("\n")

    # 1. EC2 Section
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append("1. EC2 INSTANCES INVENTORY")
    report_lines.append("--------------------------------------------------------------------------------")
    
    try:
        ec2 = boto3.client('ec2')
        response = ec2.describe_instances()
        
        instances = []
        for reservation in response.get('Reservations', []):
            for inst in reservation.get('Instances', []):
                inst_id = inst.get('InstanceId')
                inst_type = inst.get('InstanceType')
                state = inst.get('State', {}).get('Name')
                pub_ip = inst.get('PublicIpAddress', 'N/A')
                priv_ip = inst.get('PrivateIpAddress', 'N/A')
                az = inst.get('Placement', {}).get('AvailabilityZone')
                
                # Fetch Name tag
                name = "N/A"
                for tag in inst.get('Tags', []):
                    if tag.get('Key') == 'Name':
                        name = tag.get('Value')
                        break
                
                instances.append({
                    'id': inst_id,
                    'name': name,
                    'type': inst_type,
                    'state': state,
                    'public_ip': pub_ip,
                    'private_ip': priv_ip,
                    'az': az
                })
        
        if instances:
            header_format = "{:<20} | {:<20} | {:<12} | {:<10} | {:<15} | {:<12}"
            report_lines.append(header_format.format("Instance ID", "Name", "Type", "State", "Public IP", "AZ"))
            report_lines.append("-" * 98)
            for inst in instances:
                report_lines.append(header_format.format(
                    inst['id'], inst['name'], inst['type'], inst['state'], inst['public_ip'], inst['az']
                ))
            report_lines.append("-" * 98)
            report_lines.append(f"Total EC2 Instances found: {len(instances)}")
        else:
            report_lines.append("No EC2 instances found.")
            
    except ClientError as e:
        report_lines.append(f"Error retrieving EC2 resources: {e}")
        
    report_lines.append("\n")

    # 2. S3 Section
    report_lines.append("--------------------------------------------------------------------------------")
    report_lines.append("2. S3 BUCKETS & OBJECTS INVENTORY")
    report_lines.append("--------------------------------------------------------------------------------")
    
    try:
        s3 = boto3.client('s3')
        
        # Check all buckets
        buckets_response = s3.list_buckets()
        report_lines.append("Active S3 Buckets in Account:")
        for bucket in buckets_response.get('Buckets', []):
            creation_date = bucket['CreationDate'].strftime("%Y-%m-%d %H:%M:%S")
            report_lines.append(f" - {bucket['Name']} (Created: {creation_date})")
            
        report_lines.append("\n")
        
        # Inspect target bucket contents
        report_lines.append(f"Objects in Target Bucket '{BUCKET_NAME}':")
        try:
            objects_response = s3.list_objects_v2(Bucket=BUCKET_NAME)
            if 'Contents' in objects_response:
                obj_format = "   {:<40} | {:<12} | {:<25}"
                report_lines.append(obj_format.format("Object Key (Path)", "Size (Bytes)", "Last Modified"))
                report_lines.append("   " + "-" * 85)
                total_size = 0
                obj_count = 0
                for obj in objects_response['Contents']:
                    total_size += obj['Size']
                    obj_count += 1
                    report_lines.append(obj_format.format(
                        obj['Key'], str(obj['Size']), obj['LastModified'].strftime("%Y-%m-%d %H:%M:%S")
                    ))
                report_lines.append("   " + "-" * 85)
                report_lines.append(f"   Total Objects: {obj_count} | Total Size: {total_size} Bytes")
            else:
                report_lines.append("   Bucket is empty.")
        except ClientError as s3_err:
            report_lines.append(f"   Error accessing objects in bucket '{BUCKET_NAME}': {s3_err}")
            
    except ClientError as e:
        report_lines.append(f"Error retrieving S3 resources: {e}")
        
    report_lines.append("\n")
    report_lines.append("=" * 80)
    report_lines.append("End of Inventory Report")
    report_lines.append("=" * 80)

    # Print to stdout
    report_content = "\n".join(report_lines)
    print(report_content)
    
    # Save to file
    report_filename = "aws_inventory_report.txt"
    with open(report_filename, "w") as f:
        f.write(report_content)
        
    print(f"\nSuccess: Resource inventory report written to '{report_filename}'.")

if __name__ == "__main__":
    generate_inventory_report()
