import boto3
from botocore.exceptions import ClientError

def get_running_instances():
    # Initialize the EC2 client
    # You can specify a region if needed, e.g., boto3.client('ec2', region_name='us-east-1')
    ec2 = boto3.client('ec2')
    
    print("Retrieving running EC2 instances details...\n")
    
    try:
        # Filter for only running instances
        filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
        response = ec2.describe_instances(Filters=filters)
        
        instances_found = False
        
        # Header formatting
        header_format = "{:<20} | {:<20} | {:<15} | {:<12} | {:<18} | {:<15}"
        print(header_format.format("Instance ID", "Instance Name", "Instance Type", "State", "Public IPv4 Address", "Availability Zone"))
        print("-" * 110)
        
        for reservation in response.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                instances_found = True
                
                instance_id = instance.get('InstanceId', 'N/A')
                instance_type = instance.get('InstanceType', 'N/A')
                state = instance.get('State', {}).get('Name', 'N/A')
                public_ip = instance.get('PublicIpAddress', 'N/A')
                az = instance.get('Placement', {}).get('AvailabilityZone', 'N/A')
                
                # Retrieve the instance name from the tags list
                instance_name = "N/A"
                for tag in instance.get('Tags', []):
                    if tag.get('Key') == 'Name':
                        instance_name = tag.get('Value')
                        break
                
                print(header_format.format(
                    instance_id,
                    instance_name,
                    instance_type,
                    state,
                    public_ip,
                    az
                ))
                
        if not instances_found:
            print("No running EC2 instances found in the configured region.")
            
        print("-" * 110)
        print("\nRetrieval completed successfully.")
        
    except ClientError as e:
        print(f"Error fetching EC2 instances: {e}")
        print("Please check your AWS credentials/permissions for EC2.")

if __name__ == "__main__":
    get_running_instances()
