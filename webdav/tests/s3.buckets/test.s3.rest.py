import boto3
import os
from botocore.config import Config
from botocore import UNSIGNED
from botocore.exceptions import ClientError, EndpointConnectionError

# Retrieve environment variables
bucket = os.getenv('AWS_S3_BUCKET')
endpoint_url = os.getenv('AWS_S3_ENDPOINT')
print(f"Endpoint: {endpoint_url}")

if not bucket:
    raise ValueError("Bucket must be specified")


config=Config(signature_version=UNSIGNED)

try:
    session = boto3.session.Session()
    s3 = session.client(
        service_name="s3",
        endpoint_url=endpoint_url,
        config=Config(signature_version=UNSIGNED),
    )
    
    # Use the S3 client to list objects in the specified bucket and key prefix
    response = s3.list_objects_v2(Bucket=bucket, Prefix='public/250m/bdod/')
    print(response)
except EndpointConnectionError as e:
    print(f"EndpointConnectionError: Could not connect to the endpoint URL: {endpoint_url}")
    print(f"Error details: {e}")
except ClientError as e:
    print(f"ClientError: {e}")
