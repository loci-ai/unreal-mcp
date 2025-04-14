import unreal
from typing import Any

from .utils import Responses, run_on_main_thread


class ActorCommands:
    @staticmethod
    @run_on_main_thread
    def place_actor(
        asset_path: str,
        name: str,
        location: list[float],
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        Place an actor in the level.
        Args:
            asset_path: The path to the imported asset to use
            name: The name to give the new actor (must be unique)
            location: The [x, y, z] world location to spawn at
            rotation [Optional]: The [pitch, yaw, roll] rotation in degrees
            scale [Optional]: The [s] scale to apply (uniformly applied to all axes)

        Returns:
            Dict containing the created actor's properties
        """
        rotation = rotation or [0.0, 0.0, 0.0]
        scale = scale or [1.0, 1.0, 1.0]

        is_folder = unreal.EditorAssetLibrary.does_directory_exist(asset_path)
        mesh_asset = None

        if is_folder:
            assets = unreal.EditorAssetLibrary.list_assets(asset_path, recursive=True)
            for asset in assets:
                loaded = unreal.EditorAssetLibrary.load_asset(asset)
                if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                    mesh_asset = loaded
                    asset_path = asset  # update the path for the returned info
                    break
            if not mesh_asset:
                raise ValueError(f"No valid mesh asset found in folder: {asset_path}")
        else:
            # Assume it's a direct path to an asset
            mesh_asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if not isinstance(mesh_asset, (unreal.StaticMesh, unreal.SkeletalMesh)):
                raise TypeError(
                    f"Asset is not a StaticMesh or SkeletalMesh: {asset_path}"
                )

        # Determine the actor class
        if isinstance(mesh_asset, unreal.StaticMesh):
            actor_class = unreal.StaticMeshActor
        elif isinstance(mesh_asset, unreal.SkeletalMesh):
            actor_class = unreal.SkeletalMeshActor
        else:
            raise TypeError("Unsupported mesh type.")

        # Spawn actor in the world
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, unreal.Vector(*location), unreal.Rotator(*rotation)
        )
        if not actor:
            raise RuntimeError("Failed to spawn actor.")

        actor.set_actor_label(name)
        actor.set_actor_scale3d(unreal.Vector(*scale))

        # Set the mesh on the actor
        if isinstance(actor, unreal.StaticMeshActor):
            actor.static_mesh_component.set_static_mesh(mesh_asset)
        elif isinstance(actor, unreal.SkeletalMeshActor):
            actor.skeletal_mesh_component.set_skeletal_mesh(mesh_asset)

        return Responses.actor_to_json(actor)
