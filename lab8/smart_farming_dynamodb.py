"""
Lab 8: Database as a Service - Smart Farming with AWS DynamoDB
----------------------------------------------------------------
This script does three things:
1. Creates a DynamoDB table to store temperature & humidity data
   coming from IoT devices placed in 4 different farm fields.
2. Inserts sample readings (5 readings/day per device) into the table.
3. Reads the data back, calculates the average temperature per field,
   and decides whether the sprinkler should be switched On or Off.

Before running:
    pip install boto3
    aws configure   (enter your AWS access key, secret key, and region)

If you are using DynamoDB Local instead of a real AWS account, just
change the endpoint_url in get_dynamodb_resource() below.
"""

import boto3
import random
import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

TABLE_NAME = "SmartFarmingData"
REGION = "us-east-1"          # change this to your preferred AWS region

# List of IoT devices, one per field
DEVICE_IDS = ["Field1_Device01", "Field2_Device02", "Field3_Device03", "Field4_Device04"]

SPRINKLER_THRESHOLD = 25.0     # degrees Celsius


def get_dynamodb_resource():
    """Returns a boto3 DynamoDB resource.
    For DynamoDB Local, uncomment the endpoint_url line below."""
    return boto3.resource(
        "dynamodb",
        region_name=REGION,
        # endpoint_url="http://localhost:8000"   # uncomment if using DynamoDB Local
    )


def create_table(dynamodb):
    """Creates the SmartFarmingData table if it doesn't already exist."""
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "DeviceID", "KeyType": "HASH"},   # Partition key
                {"AttributeName": "Timestamp", "KeyType": "RANGE"}  # Sort key
            ],
            AttributeDefinitions=[
                {"AttributeName": "DeviceID", "AttributeType": "S"},
                {"AttributeName": "Timestamp", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        print(f"Creating table '{TABLE_NAME}', please wait...")
        table.wait_until_exists()
        print(f"Table '{TABLE_NAME}' created successfully.\n")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"Table '{TABLE_NAME}' already exists, skipping creation.\n")
        else:
            raise


def generate_sample_readings():
    """
    Simulates 5 readings/day for each device.
    Some fields are made deliberately hotter so both
    'Sprinkler On' and 'Sprinkler Off' cases show up.
    """
    today = datetime.date.today().isoformat()
    readings = []

    # Base temperature ranges per field, just to create some variation
    temp_ranges = {
        "Field1_Device01": (22, 24),   # stays below threshold
        "Field2_Device02": (26, 30),   # stays above threshold
        "Field3_Device03": (24, 27),   # borderline
        "Field4_Device04": (28, 32),   # clearly above threshold
    }

    for device_id in DEVICE_IDS:
        low, high = temp_ranges[device_id]
        for i in range(5):
            hour = 6 + (i * 3)   # readings spread across the day, e.g. 6am, 9am, 12pm...
            timestamp = f"{today}T{hour:02d}:00:00"
            temperature = round(random.uniform(low, high), 2)
            humidity = round(random.uniform(40, 70), 2)
            readings.append({
                "DeviceID": device_id,
                "Timestamp": timestamp,
                "Temperature": Decimal(str(temperature)),
                "Humidity": Decimal(str(humidity))
            })
    return readings


def insert_readings(dynamodb, readings):
    """Inserts all sample readings into the DynamoDB table."""
    table = dynamodb.Table(TABLE_NAME)
    with table.batch_writer() as batch:
        for item in readings:
            batch.put_item(Item=item)
    print(f"Inserted {len(readings)} readings into '{TABLE_NAME}'.\n")


def analyse_and_control_sprinkler(dynamodb):
    """
    For each device, queries all readings for today, calculates the
    average temperature, and prints the sprinkler decision.
    """
    table = dynamodb.Table(TABLE_NAME)
    today = datetime.date.today().isoformat()

    print("----- Daily Analysis & Sprinkler Decision -----\n")
    for device_id in DEVICE_IDS:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("DeviceID").eq(device_id)
            & boto3.dynamodb.conditions.Key("Timestamp").begins_with(today)
        )
        items = response.get("Items", [])

        if not items:
            print(f"{device_id}: No readings found for today.\n")
            continue

        avg_temp = sum(Decimal(item["Temperature"]) for item in items) / len(items)
        avg_temp = round(float(avg_temp), 2)

        decision = "Sprinkler On" if avg_temp > SPRINKLER_THRESHOLD else "Sprinkler Off"

        print(f"Device: {device_id}")
        print(f"Readings today: {len(items)}")
        print(f"Average Temperature: {avg_temp}°C")
        print(f"Decision: {decision}\n")


def main():
    dynamodb = get_dynamodb_resource()

    create_table(dynamodb)

    readings = generate_sample_readings()
    insert_readings(dynamodb, readings)

    analyse_and_control_sprinkler(dynamodb)


if __name__ == "__main__":
    main()
