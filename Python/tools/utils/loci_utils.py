import json
from aiohttp import ClientError
import boto3
import certifi
from pymongo import MongoClient


def get_secret(secret_name: str, region_name: str = "eu-west-2") -> dict[str, str]:
    # Create a Secrets Manager client
    session = boto3.session.Session()  # type: ignore
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(f"Error retrieving secret: {e}")
        raise e

    # Decrypts secret using the associated KMS key.
    return json.loads(get_secret_value_response["SecretString"])


SECRETS_DICT = get_secret("loci/dev")
MONGO_CLIENT = MongoClient(SECRETS_DICT["MONGO_DB_URL"], tlsCAFile=certifi.where())
MONGO_MASTER_ASSET_COLLECTION = MONGO_CLIENT["main"]["assets_master"]
S3_CLIENT = boto3.client("s3")
S3_BUCKET = "loci-assets"
