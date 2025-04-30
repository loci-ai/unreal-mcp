import base64
import logging
import os
import tempfile
from time import time
from uuid import uuid4

import boto3
import requests
from env import LOCI_API_KEY
from mcp.server.fastmcp import Context, FastMCP

# Get logger
logger = logging.getLogger("UnrealMCP")


S3_CLIENT = boto3.client("s3")


def register_genai_tools(mcp: FastMCP):

    @mcp.tool()
    def do_nothing(ctx: Context):
        """A tool that does nothing and returns a success message.

        Args:
            ctx: The MCP context
        Returns:
            Dict containing keys "status" and "message"
            "status" indicates success or failure
            "message" provides additional information
        """
        return {
            "status": "success",
            "message": "This tool does nothing, but it works!",
        }

    @mcp.tool()
    def generate_image_from_text_prompt(ctx: Context, text_prompt: str, seed:int=0):
        """Generate an image from a text prompt.

        Args:
            ctx: The MCP context
            text_prompt: The text prompt to generate an image from. (Max 120 characters)
            The prompt should be a single sentence and not contain any special characters.
            seed: The seed to use for the image generation. Use different seeds for variation (Optional)

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
                "x-api-key": LOCI_API_KEY,
            }

            # ------------------------------- text to image ------------------------------ #
            text_to_image_url = "https://dev.loci-api.com/image/generate"

            data = {"prompt": text_prompt, "seed": seed}

            image_response = requests.post(
                text_to_image_url, headers=headers, data=data
            )
            image_response.raise_for_status()
            image_contents_base64 = image_response.json()["contents_base64"]
            logger.info(f"Successully generated image from text prompt")

            temp_dir = tempfile.mkdtemp()

            local_path = f"{temp_dir}/ai_generated_image_{uuid4()}.png"  # type: ignore

            with open(local_path, "wb") as f:
                f.write(base64.b64decode(image_contents_base64))

            logger.info(
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
    def generate_asset_from_image(ctx: Context, image_path: str, generate_textures: bool = True):
        """Generate a 3D model from an image.

        Args:
            ctx: The MCP context
            image_path: The local path to the image.
            generate_textures: Whether to generate textures for the 3D model. (Optional)
            The default is True, which means textures will be generated.

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
                "x-api-key": LOCI_API_KEY,
            }

            # -------------------------------- image to 3D ------------------------------- #
            image_to_3d_url = "https://dev.loci-api.com/3d/generate"

            files = {"file": open(file=image_path, mode="rb")}

            data = {"model_name": "hunyuan", "generate_textures": generate_textures}

            asset_response = requests.post(
                image_to_3d_url, headers=headers, data=data, files=files
            )
            asset_response.raise_for_status()
            presigned_url = asset_response.json()["presigned_url"]
            logger.info(f"Successully generated 3d asset from image")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".glb") as tmp_file:
                # Download the file content
                response = requests.get(presigned_url)
                response.raise_for_status()  # Raise error if download failed

                # Write content to temp file
                tmp_file.write(response.content)

                # Get temp file path
                temp_file_path = tmp_file.name

            logger.info(
                f"Generating a 3d asset from text prompt took {time()-tic} seconds. Asset saved to {presigned_url}"
            )

            return {
                "status": "success",
                "message": "Asset successfully generated",
                "file_path": temp_file_path,
            }
        except Exception as e:
            return {"error": f"Failed to generate asset from prompt: {str(e)}"}

    logger.info("GenAI tools registered successfully")
