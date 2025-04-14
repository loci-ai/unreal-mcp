import logging
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse
import boto3
import requests

from mcp.server.fastmcp import FastMCP, Context

# Get logger
logger = logging.getLogger("UnrealMCP")

# -----------------------------------------
# -----------------------------------------
LOCI_API_KEY = os.environ["LOCI_API_KEY"]
# -----------------------------------------
# -----------------------------------------

S3_CLIENT = boto3.client("s3")
MAX_NUM_RESULTS = 5
BUCKET = "loci-assets"

def register_fab_tools(mcp: FastMCP):

    @mcp.tool()
    def search_fab_assets(ctx: Context, text_query=None):
        """Search assets in FAB.
        Args:
            ctx: The MCP context
            text_query: Query string to search in FAB

        Returns:
            Dict containing keys "assets" and "returned_count"
            "assets" is a dictionary with asset IDs as keys and relevance scores as values.
            "returned_count" is the number of assets returned.
        """
        max_num_results=MAX_NUM_RESULTS

        try:
            url = "https://dev.loci-api.com/3d/search"
            params = {
                "page_size": max_num_results,
                "page_number": 1,
                "should_translate": "false",
                "debug": "true",
            }
            headers = {
                "accept": "application/json",
                "x-api-key": LOCI_API_KEY,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {
                "text_query": text_query,
                "model_name": "loci",
                "similarity_threshold": 0.85,
            }

            response = requests.post(url, headers=headers, params=params, data=data)
            hits = response.json().get("hits")
            assets = {h["asset_id"]: {"name": h["filename"].split(".")[0], "relevance": h["similarity"]} for h in hits}
            return {"assets": assets, "returned_count": len(assets)}

        except Exception as e:
            return {"error": f"FAB search failed: {str(e)}"}

    @mcp.tool()
    def download_fab_asset(ctx: Context, asset_id: str):
        """Download a FAB asset.
        Args:
            ctx: The MCP context
            asset_id: The ID of the asset to download
        Returns:
            Dict containing keys "status", "message", and "file_path"
            "status" indicates success or failure
            "message" provides additional information
            "file_path" is the local path to the downloaded asset
        """
        try:
            asset_path=f"s3://loci-assets/dataset_Objaverse-V1/asset_{asset_id}/{asset_id}.glb"

            temp_dir = tempfile.mkdtemp()
            try:
                # Parse the S3 URI
                parsed = urlparse(asset_path)
                s3_key = parsed.path.lstrip('/')
                file_name = Path(s3_key).name
                local_path = Path(temp_dir) / file_name

                # Download the file
                S3_CLIENT.download_file(BUCKET, s3_key, str(local_path))

            except Exception as e:
                return {"error": f"Failed to download model: {str(e)}"}

            return {
                "status": "success",
                "message": "Asset downloaded successfully",
                "file_path": local_path,
            }
        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}

    logger.info("FAB tools registered successfully")
