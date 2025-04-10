import json
import logging
import os
import tempfile
import boto3
import certifi
from botocore.exceptions import ClientError
from pymongo import MongoClient

from mcp.server.fastmcp import FastMCP, Context

# Get logger
logger = logging.getLogger("UnrealMCP")


def get_secret(secret_name: str, region_name: str = "eu-west-2") -> dict[str, str]:
    # Create a Secrets Manager client
    session = boto3.session.Session()  # type: ignore
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    return json.loads(get_secret_value_response["SecretString"])


S3_CLIENT = boto3.client("s3")

secrets_dict = get_secret("loci/dev")
MONGO_DB_URL = secrets_dict["MONGO_DB_URL"]


def register_fab_tools(mcp: FastMCP):

    @mcp.tool()
    def search_fab_assets(ctx: Context, text_query=None):
        """Search for assets from FAB with optional filtering"""
        try:
            asset_id = "00000054c36d44a2a483bdbff31d8edf"
            asset_data = {
                "name": "Arjun G Round Roller",
                "download_count": 1000,
                "asset_path": f"s3://loci-assets/dataset_Objaverse-V1/asset_{asset_id}/{asset_id}.glb",
            }
            assets = {asset_id: asset_data}

            limited_assets = assets.copy()

            return {
                "assets": assets,
                "total_count": len(assets),
                "returned_count": len(limited_assets),
            }

        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def download_fab_asset(ctx: Context, asset_id: str):
        try:
            # TODO get asset_path in search directly to avoid mongo call
            mongo_query = {"source_id": asset_id}
            mongo_projection = {"source_id": 1, "asset_path": 1}
            client = MongoClient(MONGO_DB_URL, tlsCAFile=certifi.where())
            db = client["main"]
            master_asset_collection = db["assets_master"]
            asset = master_asset_collection.find(mongo_query, mongo_projection)
            asset = list(asset)[0]
            asset_path = asset["asset_path"]

            bucket = "loci-assets"
            object_key = asset_path.replace("s3://loci-assets/", "")
            temp_dir = tempfile.mkdtemp()
            try:
                # Download the main model file
                main_file_name = asset_path.split("/")[-1]
                main_file_path = os.path.join(temp_dir, main_file_name)
                S3_CLIENT.download_file(bucket, object_key, main_file_path)

            except Exception as e:
                return {"error": f"Failed to download model: {str(e)}"}

            return {
                "status": "success",
                "message": "Asset downloaded successfully",
                "file_path": main_file_path,
            }
        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}

    logger.info("FAB tools registered successfully")
