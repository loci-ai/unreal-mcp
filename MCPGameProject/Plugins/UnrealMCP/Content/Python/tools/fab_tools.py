import tempfile
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

import requests
from loci_utils import LOCI_ASSETS_S3_BUCKET, MONGO_MASTER_ASSET_COLLECTION, S3_CLIENT
from mcp.server.fastmcp import Context, FastMCP

from .utils.search import Asset, get_asset_index, search

MAX_RESULTS = 5
FAB_SEARCH_URL = "https://www.fab.com/i/listings/search"


def get_mongo_assets(key_uid: str, key_title: str, uids: list[str]) -> list[Asset]:
    """Filter asset IDs in MongoDB.
    Args:
        assets: List of Asset objects to filter.
    Returns:
        List of asset IDs that are present in MongoDB.
    """

    def recursive_get(key: str, x: dict) -> str:
        """Recursively get value of mongodb key defined with dot splits"""
        keys = key.split(".")
        for k in keys:
            if k in x:
                x = x[k]
            else:
                return None
        return x

    try:
        mongo_query = {key_uid: {"$in": uids}, "asset_path": {"$exists": True}}
        mongo_projection = {key_uid: 1, key_title: 1, "asset_path": 1}
        assets = MONGO_MASTER_ASSET_COLLECTION.find(mongo_query, mongo_projection)
        assets = [
            Asset(
                uid=recursive_get(key_uid, a),
                title=recursive_get(key_title, a),
                asset_s3_path=a["asset_path"],
            )
            for a in assets
        ]
        return assets

    except Exception as e:
        print(f"Error filtering asset IDs in MongoDB: {e}")
        return []


def register_fab_tools(mcp: FastMCP):
    @mcp.tool()
    def search_fab_assets(
        ctx: Context, text_query=None, max_results: int = MAX_RESULTS
    ):
        """Search assets in FAB.
        Args:
            ctx: The MCP context
            text_query: Query string to search in FAB
            max_results: Maximum number of results to return

        Returns:
            Dict containing keys "assets" and "returned_count"
            "assets" is a list of dictionaries with keys "uid", "title", and "asset_s3_path".
            "returned_count" is the number of assets returned.
        """
        params = {
            "listing_types": "3d-model",
            "asset_formats": "glb",  # Needed as we only ingested these - eventually remove
            "q": text_query,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "accept": "application/json",
        }

        response = requests.get(url=FAB_SEARCH_URL, headers=headers, params=params)
        results = response.json()["results"]
        result_uids = [r["uid"] for r in results]
        assets = get_mongo_assets(
            key_uid="metadata.source.fab._source.uid",
            key_title="metadata.source.fab._source.title",
            uids=result_uids,
        )

        if len(assets) < max_results and len(results) > max_results:
            while len(assets) < max_results:
                next_cursor = response.json()["cursors"]["next"]
                params["cursor"] = next_cursor
                response = requests.get(
                    url=FAB_SEARCH_URL, headers=headers, params=params
                )
                results = response.json()["results"]
                if len(results) == 0:
                    break

                result_uids = [r["uid"] for r in results]
                new_assets = get_mongo_assets(
                    key_uid="metadata.source.fab._source.uid",
                    key_title="metadata.source.fab._source.title",
                    uids=result_uids,
                )
                assets.extend(new_assets)
                if len(assets) > max_results:
                    break

        assets = [asdict(a) for a in assets[:max_results]]
        return {"assets": assets, "returned_count": len(assets)}

    @mcp.tool()
    def search_loci_assets(
        ctx: Context, text_query=None, max_results: int = MAX_RESULTS
    ):
        """Search assets in LOCI.
        Args:
            ctx: The MCP context
            text_query: Query string to search
            max_results: Maximum number of results to return

        Returns:
            Dict containing keys "assets" and "returned_count"
            "assets" is a list of dictionaries with keys "uid", "title", and "asset_s3_path".
            "returned_count" is the number of assets returned.
        """

        try:

            index = get_asset_index()
            assets = search(query=text_query, index=index, k=max_results)
            assets = [asdict(a) for a in assets]
            return {"assets": assets, "returned_count": len(assets)}

        except Exception as e:
            return {"error": f"FAB search failed: {str(e)}"}

    # @mcp.tool()
    # def search_loci_assets(
    #     ctx: Context, text_query=None, max_results: int = MAX_RESULTS
    # ):
    #     """Search assets in LOCI.
    #     Args:
    #         ctx: The MCP context
    #         text_query: Query string to search
    #         max_results: Maximum number of results to return

    #     Returns:
    #         Dict containing keys "assets" and "returned_count"
    #         "assets" is a list of dictionaries with keys "uid", "title", and "asset_s3_path".
    #         "returned_count" is the number of assets returned.
    #     """

    #     try:
    #         url = "https://dev.loci-api.com/3d/search"
    #         params = {
    #             "page_size": max_results,
    #             "page_number": 1,
    #             "should_translate": "false",
    #             "debug": "true",
    #         }
    #         headers = {
    #             "accept": "application/json",
    #             "x-api-key": LOCI_API_KEY,
    #             "Content-Type": "application/x-www-form-urlencoded",
    #         }
    #         data = {
    #             "text_query": text_query,
    #             "model_name": "loci",
    #             "similarity_threshold": 0.5,
    #         }

    #         response = requests.post(url, headers=headers, params=params, data=data)
    #         results = response.json().get("hits")
    #         results = sorted(results, key=lambda x: x["similarity"], reverse=True)
    #         results_uids = [h["asset_id"] for h in results]

    #         assets = get_mongo_assets(
    #             key_uid="source_id",
    #             key_title="asset_name",
    #             uids=results_uids,
    #         )
    #         assets = [asdict(a) for a in assets[:max_results]]
    #         return {"assets": assets, "returned_count": len(assets)}

    #     except Exception as e:
    #         return {"error": f"FAB search failed: {str(e)}"}

    @mcp.tool()
    def download_s3_asset(ctx: Context, asset_s3_path: str):
        """Download a FAB asset.
        Args:
            ctx: The MCP context
            asset_s3_path: S3 URI of the asset to download
        Returns:
            Dict containing keys "status", "message", and "file_path"
            "status" indicates success or failure
            "message" provides additional information
            "file_path" is the local path to the downloaded asset
        """
        try:
            temp_dir = tempfile.mkdtemp()
            try:
                # Parse the S3 URI
                parsed = urlparse(asset_s3_path)
                s3_key = parsed.path.lstrip("/")
                file_name = Path(s3_key).name
                local_path = Path(temp_dir) / file_name

                # Download the file
                S3_CLIENT.download_file(LOCI_ASSETS_S3_BUCKET, s3_key, str(local_path))

            except Exception as e:
                return {"error": f"Failed to download model: {str(e)}"}

            return {
                "status": "success",
                "message": "Asset downloaded successfully",
                "file_path": local_path,
            }

        except Exception as e:
            return {"error": f"Failed to download asset: {str(e)}"}
