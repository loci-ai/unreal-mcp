import base64
import tempfile
from pathlib import Path
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
import unreal
from loci_utils import ASSET_DOWNLOADS_S3_BUCKET, LOCI_MASTER_API_KEY, S3_CLIENT
from mcp.server.fastmcp import Context, FastMCP


def register_genai_tools(mcp: FastMCP):

    @mcp.tool()
    def generate_image_from_text_prompt(ctx: Context, text_prompt=None):
        """Generate an image from a text prompt.

        Args:
            ctx: The MCP context
            text_prompt: The text prompt to generate an image from.

        Returns:
            Dict containing keys "status", "message", and "file_path"
            "status" indicates success or failure
            "message" provides additional information
            "file_path" is the local path to the generated image
        """

        try:
            tic = time()
            headers = {
                "accept": "application/json",
                "x-api-key": LOCI_MASTER_API_KEY,
            }

            # ------------------------------- text to image ------------------------------ #
            text_to_image_url = "https://dev.loci-api.com/image/generate"

            data = {"prompt": text_prompt, "positive_prompt": ""}

            image_response = requests.post(
                text_to_image_url, headers=headers, data=data
            )
            image_response.raise_for_status()
            image_contents_base64 = image_response.json()["contents_base64"]
            unreal.log(f"Successully generated image from text prompt")

            temp_dir = tempfile.mkdtemp()

            local_path = f"{temp_dir}/ai_generated_image_{uuid4()}.png"  # type: ignore

            with open(local_path, "wb") as f:
                f.write(base64.b64decode(image_contents_base64))

            unreal.log(
                f"Generating an image from text prompt took {time()-tic} seconds"
            )

            return {
                "status": "success",
                "message": "Image successfully generated",
                "file_path": local_path,
            }
        except Exception as e:
            return {"error": f"Failed to generate image from prompt: {str(e)}"}

    @mcp.tool()
    def generate_asset_from_image(ctx: Context, image_path=None):
        """Generate a 3D model from an image.
        Note: before generating the asset, show the image to the user
        and check if they want to make any changes

        Args:
            ctx: The MCP context
            image_path: The local path to the image.

        Returns:
            Dict containing keys "status", "message", and "file_path"
            "status" indicates success or failure
            "message" provides additional information
            "file_path" is the local path to the generated asset
        """

        try:
            tic = time()
            headers = {
                "accept": "application/json",
                "x-api-key": LOCI_MASTER_API_KEY,
            }

            # -------------------------------- image to 3D ------------------------------- #
            image_to_3d_url = "https://dev.loci-api.com/3d/generate"

            files = {"file": open(file=image_path, mode="rb")}

            data = {"model_name": "hunyuan", "generate_textures": False}

            asset_response = requests.post(
                image_to_3d_url, headers=headers, data=data, files=files
            )
            asset_response.raise_for_status()
            asset_presigned_url = asset_response.json()["presigned_url"]
            unreal.log(f"Successully generated 3d asset from image")

            temp_dir = tempfile.mkdtemp()
            # Parse the S3 URI
            try:
                parsed = urlparse(asset_presigned_url)
                s3_key = parsed.path.lstrip("/")
                file_name = Path(s3_key).name
                local_path = Path(temp_dir) / file_name

                # Download the file
                S3_CLIENT.download_file(
                    ASSET_DOWNLOADS_S3_BUCKET, s3_key, str(local_path)
                )
            except Exception as e:
                return {"error": f"Failed to download model: {str(e)}"}

            unreal.log(
                f"Generating a 3d asset from text prompt took {time()-tic} seconds. Asset saved to {local_path}"
            )

            return {
                "status": "success",
                "message": "Asset successfully generated",
                "file_path": local_path,
            }
        except Exception as e:
            return {"error": f"Failed to generate asset from prompt: {str(e)}"}

    unreal.log("GenAI tools registered successfully")
