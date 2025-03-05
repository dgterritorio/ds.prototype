import boto3
import os
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

# Retrieve environment variables
bucket = os.getenv('AWS_S3_BUCKET')
endpoint_url = os.getenv('AWS_S3_ENDPOINT')
print(f"Endpoint: {endpoint_url}")

if not bucket:
    raise ValueError("Bucket must be specified")

# Config without specific region
config_params = {
    "retries": {"max_attempts": 10, "mode": "adaptive"},
    "connect_timeout": 5,
    "read_timeout": 5,
    "max_pool_connections": 200,
    "use_dualstack_endpoint": False,
    "use_fips_endpoint": False,
    "region_name": "aws-global",  # Placeholder for non-region-specific service
    "s3": {
        "use_accelerate_endpoint": False,
        "payload_signing_enabled": False,
        "use_global_endpoint": False,
        "use_arn_region": False,
        "addressing_style": "path",
    },
}

try:
    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        config=Config(**config_params),
    )
    
    # Use the S3 client to list objects in the specified bucket and key prefix
    response = s3.list_objects_v2(Bucket=bucket, Prefix='public/250m/bdod/')
    print(response)
except EndpointConnectionError as e:
    print(f"EndpointConnectionError: Could not connect to the endpoint URL: {endpoint_url}")
    print(f"Error details: {e}")
except ClientError as e:
    print(f"ClientError: {e}")
