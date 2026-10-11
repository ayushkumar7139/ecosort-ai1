"""
EcoSort AI — DynamoDB Table Setup Script

Run once to create the DynamoDB table for scan history.
Requires AWS credentials with DynamoDB permissions.

Usage:
    python infrastructure/dynamodb_setup.py

Environment variables:
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, DYNAMODB_TABLE
"""

import boto3
import os
from botocore.exceptions import ClientError

REGION = os.getenv("AWS_REGION", "us-east-1")
TABLE_NAME = os.getenv("DYNAMODB_TABLE", "ecosort-scans")


def create_table():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",  # On-demand — no provisioned capacity needed
            Tags=[
                {"Key": "Project", "Value": "EcoSort AI"},
                {"Key": "Environment", "Value": "development"},
            ],
        )
        table.wait_until_exists()
        print(f"✅ DynamoDB table '{TABLE_NAME}' created successfully in {REGION}.")
        print(f"   ARN: {table.table_arn}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️  Table '{TABLE_NAME}' already exists.")
        else:
            print(f"❌ Error creating table: {e}")
            raise


if __name__ == "__main__":
    create_table()
