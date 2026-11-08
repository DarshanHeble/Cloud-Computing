"""
AWS Static Site + Auto Scaling + Lambda automation (boto3)
------------------------------------------------------------
Covers R1-R5 of the assignment in one script.

Run this LOCALLY (or in AWS CloudShell), not inside a chat sandbox.
Configure credentials beforehand with `aws configure` or environment
variables. Never paste your access key / secret into a chat window.

Fill in the CONFIG section below with values from your own AWS account,
then run:  python aws_infra_automation.py
"""

import base64
import json
import time
import zipfile
import io
import boto3

# --------------------------------------------------------------------------
# CONFIG - fill these in for your account before running
# --------------------------------------------------------------------------
REGION            = "ap-south-1"          # change to your region
KEY_PAIR_NAME       = "my-keypair"          # existing EC2 key pair (make sure to create this)
AMI_ID             = "ami-0f5ee92e2d63afc18"  # Amazon Linux 2023 in ap-south-1, change per region
INSTANCE_TYPE       = "t2.micro"
MY_NAME             = "Your Name"
MY_BIO              = "A short bio about yourself goes here."
LAMBDA_ROLE_NAME     = "assignment-lambda-role"

ec2      = boto3.client("ec2", region_name=REGION)
elbv2    = boto3.client("elbv2", region_name=REGION)
autoscaling = boto3.client("autoscaling", region_name=REGION)
iam      = boto3.client("iam", region_name=REGION)
lambda_client = boto3.client("lambda", region_name=REGION)

def get_default_vpc_and_subnets():
    # Discover default VPC
    try:
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        if not vpcs['Vpcs']:
            raise Exception("No default VPC found in this region.")
        vpc_id = vpcs['Vpcs'][0]['VpcId']
        
        # Discover subnets for the default VPC
        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
        subnet_ids = [s['SubnetId'] for s in subnets['Subnets']]
        if len(subnet_ids) < 2:
            raise Exception("Need at least 2 subnets in different AZs for ALB.")
        return vpc_id, subnet_ids
    except Exception as e:
        print(f"Error fetching VPC/Subnets: {e}")
        return "vpc-XXXXXXXX", ["subnet-AAAAAAAA", "subnet-BBBBBBBB"]

VPC_ID, SUBNET_IDS = get_default_vpc_and_subnets()
print(f"Using VPC: {VPC_ID}")
print(f"Using Subnets: {SUBNET_IDS}")

# --------------------------------------------------------------------------
# R1 - Security group + user-data static page + Launch Template
# --------------------------------------------------------------------------
def get_default_security_group():
    """Lab/Academy accounts often block ec2:CreateSecurityGroup.
    Fall back to the VPC's existing default security group instead."""
    resp = ec2.describe_security_groups(
        Filters=[
            {"Name": "vpc-id", "Values": [VPC_ID]},
            {"Name": "group-name", "Values": ["default"]},
        ]
    )
    sg_id = resp["SecurityGroups"][0]["GroupId"]
    print(f"Using existing default security group: {sg_id}")
    return sg_id


def create_security_group():
    try:
        sg = ec2.create_security_group(
            GroupName=f"assignment-sg-{int(time.time())}",
            Description="Allow HTTP and SSH",
            VpcId=VPC_ID,
        )
        sg_id = sg["GroupId"]
        print(f"Security group created: {sg_id}")
    except ec2.exceptions.ClientError as e:
        if "UnauthorizedOperation" in str(e):
            print("No permission to create a new security group, "
                  "falling back to the VPC's default security group.")
            sg_id = get_default_security_group()
        else:
            raise

    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
                {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                 "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            ],
        )
    except ec2.exceptions.ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            pass  # rule already exists, fine
        elif "UnauthorizedOperation" in str(e):
            print("Warning: not authorized to modify security group rules either. "
                  "Ask your lab admin, or add the HTTP/SSH inbound rules "
                  "manually from the console if it allows that.")
        else:
            raise

    return sg_id


def build_user_data():
    html_page = f"""<!DOCTYPE html>
<html>
<head><title>{MY_NAME}</title></head>
<body style="font-family: Arial; text-align: center; margin-top: 50px;">
  <h1>{MY_NAME}</h1>
  <img src="https://via.placeholder.com/150" alt="profile photo"><br>
  <p>{MY_BIO}</p>
</body>
</html>"""
    script = f"""#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
cat > /var/www/html/index.html << 'EOF'
{html_page}
EOF
"""
    return base64.b64encode(script.encode()).decode()


def create_launch_template(sg_id):
    user_data = build_user_data()
    resp = ec2.create_launch_template(
        LaunchTemplateName=f"assignment-lt-{int(time.time())}",
        LaunchTemplateData={
            "ImageId": AMI_ID,
            "InstanceType": INSTANCE_TYPE,
            "KeyName": KEY_PAIR_NAME,
            "SecurityGroupIds": [sg_id],
            "UserData": user_data,
        },
    )
    lt_id = resp["LaunchTemplate"]["LaunchTemplateId"]
    print(f"Launch template created: {lt_id}")
    return lt_id


# --------------------------------------------------------------------------
# R2 - Application Load Balancer, target group, listener
# --------------------------------------------------------------------------
def create_alb(sg_id):
    suffix = int(time.time())
    alb = elbv2.create_load_balancer(
        Name=f"assignment-alb-{suffix}",
        Subnets=SUBNET_IDS,
        SecurityGroups=[sg_id],
        Scheme="internet-facing",
        Type="application",
    )
    alb_arn = alb["LoadBalancers"][0]["LoadBalancerArn"]
    alb_dns = alb["LoadBalancers"][0]["DNSName"]

    tg = elbv2.create_target_group(
        Name=f"assignment-tg-{suffix}",
        Protocol="HTTP",
        Port=80,
        VpcId=VPC_ID,
        HealthCheckPath="/",
    )
    tg_arn = tg["TargetGroups"][0]["TargetGroupArn"]

    elbv2.create_listener(
        LoadBalancerArn=alb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}],
    )
    print(f"ALB created, DNS name: {alb_dns}")
    return alb_arn, tg_arn, alb_dns


# --------------------------------------------------------------------------
# R3 - Auto Scaling Group with scheduled scaling (business hours vs off-peak)
# --------------------------------------------------------------------------
def create_asg_with_schedule(lt_id, tg_arn):
    suffix = int(time.time())
    asg_name = f"assignment-asg-{suffix}"
    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchTemplate={"LaunchTemplateId": lt_id, "Version": "$Latest"},
        MinSize=1,
        MaxSize=5,
        DesiredCapacity=1,
        VPCZoneIdentifier=",".join(SUBNET_IDS),
        TargetGroupARNs=[tg_arn],
        HealthCheckType="ELB",
        HealthCheckGracePeriod=120,
    )
    # Scale up at 9 AM (peak hours)
    autoscaling.put_scheduled_update_group_action(
        AutoScalingGroupName=asg_name,
        ScheduledActionName="scale-up-business-hours",
        Recurrence="0 9 * * *",   # every day at 09:00 UTC, adjust for your TZ
        MinSize=3,
        MaxSize=5,
        DesiredCapacity=3,
    )
    # Scale down at 6 PM (off peak)
    autoscaling.put_scheduled_update_group_action(
        AutoScalingGroupName=asg_name,
        ScheduledActionName="scale-down-off-peak",
        Recurrence="0 18 * * *",  # every day at 18:00 UTC, adjust for your TZ
        MinSize=1,
        MaxSize=2,
        DesiredCapacity=1,
    )
    print("Auto Scaling Group with scheduled actions created.")


# --------------------------------------------------------------------------
# R5 - Lambda function, IAM role, trigger (Function URL), invoke + verify
# --------------------------------------------------------------------------
LAMBDA_SOURCE = '''
import json

def lambda_handler(event, context):
    body = event
    if "body" in event and event["body"]:
        try:
            body = json.loads(event["body"])
        except Exception:
            body = event

    name = body.get("name", "Student")
    number = body.get("number", 0)

    try:
        number = int(number)
        squared = number ** 2
    except (ValueError, TypeError):
        squared = None

    result = {
        "message": f"Hello, {name}!",
        "input_number": number,
        "processed_output": squared
    }

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
'''


def create_lambda_role():
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }],
    }
    try:
        role = iam.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )
        role_arn = role["Role"]["Arn"]
        iam.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        print("Waiting for IAM role to propagate...")
        time.sleep(10)
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = iam.get_role(RoleName=LAMBDA_ROLE_NAME)["Role"]["Arn"]
    return role_arn


def deploy_lambda(role_arn):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("lambda_function.py", LAMBDA_SOURCE)
    buf.seek(0)

    try:
        fn = lambda_client.create_function(
            FunctionName="assignment-processor",
            Runtime="python3.12",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": buf.read()},
            Timeout=10,
        )
        fn_arn = fn["FunctionArn"]
    except lambda_client.exceptions.ResourceConflictException:
        fn_arn = lambda_client.get_function(FunctionName="assignment-processor")["Configuration"]["FunctionArn"]

    # R5.4 - trigger: a public Function URL, simplest trigger to test with curl/browser
    try:
        url_config = lambda_client.create_function_url_config(
            FunctionName="assignment-processor",
            AuthType="NONE",
        )
        lambda_client.add_permission(
            FunctionName="assignment-processor",
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE",
        )
        fn_url = url_config["FunctionUrl"]
    except lambda_client.exceptions.ResourceConflictException:
        fn_url = lambda_client.get_function_url_config(FunctionName="assignment-processor")["FunctionUrl"]

    print(f"Lambda deployed: {fn_arn}")
    print(f"Function URL trigger: {fn_url}")
    return fn_url


def invoke_and_verify_lambda():
    # R5.5 / R5.6 - direct invoke via boto3, then print result
    payload = {"name": "Aarav", "number": 7}
    resp = lambda_client.invoke(
        FunctionName="assignment-processor",
        Payload=json.dumps(payload).encode(),
    )
    result = json.loads(resp["Payload"].read())
    print("Lambda invocation result:")
    print(json.dumps(result, indent=2))
    return result


# --------------------------------------------------------------------------
# Main orchestration
# --------------------------------------------------------------------------
if __name__ == "__main__":
    sg_id = create_security_group()
    lt_id = create_launch_template(sg_id)
    alb_arn, tg_arn, alb_dns = create_alb(sg_id)
    create_asg_with_schedule(lt_id, tg_arn)

    role_arn = create_lambda_role()
    fn_url = deploy_lambda(role_arn)
    invoke_and_verify_lambda()

    print("\nDone. Once instances pass health checks, open this in a browser:")
    print(f"http://{alb_dns}")
    print(f"Test the Lambda trigger directly at: {fn_url}")
