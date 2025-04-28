import unreal
from typing import Any

from .utils import Responses


class ActorCommands:

    @staticmethod
    def place_actor(
        asset_path: str,
        name: str,
        location: list[float],
        rotation: float = 0.0,
        scale: float = 1.0,
    ) -> dict[str, Any]:
        """
        Place an actor in the level.
        Args:
            asset_path: The path to the imported asset to use
            name: The name to give the new actor (must be unique)
            location: The [x, y, z] world location to spawn at
            rotation [Optional]: The z axis rotation in degrees
            scale [Optional]: The [s] scale to apply (uniformly applied to all axes)

        Returns:
            Dict containing the created actor's properties
        """

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

        bounds = mesh_asset.get_bounding_box()
        max_dim = max(
            bounds.max.x - bounds.min.x,
            bounds.max.y - bounds.min.y,
            bounds.max.z - bounds.min.z,
        )
        scale = scale / max_dim * 100.0

        loc_v = unreal.Vector(*location)
        rot_v = unreal.Rotator(0.0, 0.0, rotation)
        scale_v = unreal.Vector(scale, scale, scale)

        hit_result = unreal.SystemLibrary.line_trace_single(
            unreal.EditorLevelLibrary.get_editor_world(),
            start=unreal.Vector(location[0], location[1], 2000),
            end=unreal.Vector(location[0], location[1], -2000),
            trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
            trace_complex=False,
            actors_to_ignore=[],
            draw_debug_type=unreal.DrawDebugTrace.NONE,
            ignore_self=True,
        )
        if hit_result:
            hit_result = hit_result.to_tuple()
            loc_v = hit_result[4]

        # Spawn actor in the world
        actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
            actor_class, loc_v, rot_v
        )
        if not actor:
            raise RuntimeError("Failed to spawn actor.")

        actor.set_actor_label(name)
        actor.set_actor_scale3d(scale_v)

        # Set the mesh on the actor
        if isinstance(actor, unreal.StaticMeshActor):
            actor.static_mesh_component.set_static_mesh(mesh_asset)
        elif isinstance(actor, unreal.SkeletalMeshActor):
            actor.skeletal_mesh_component.set_skeletal_mesh(mesh_asset)

        return Responses.actor_to_json(actor)

    @staticmethod
    def place_multiple_actors(
        asset_path: str,
        prefix_name: str,
        locations: list[list[float]],
        rotations: list[float] = None,
        scales: list[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Place multiple actors in the level.
        Args:
            asset_path: Folder path to the imported assets to use
            prefix: Prefix to add to the actor names
            locations: List of [x, y, z] world locations to spawn at
            rotations: [Optional] List of z axis rotations in degrees
            scales: [Optional] List of [s] scales to apply (uniformly applied to all axes)
        Returns:
            Success/error response
        """
        import random

        mesh_assets = []
        rotations = rotations or [0.0] * len(locations)
        scales = scales or [1.0] * len(locations)

        is_folder = unreal.EditorAssetLibrary.does_directory_exist(asset_path)
        if is_folder:
            assets = unreal.EditorAssetLibrary.list_assets(asset_path, recursive=True)
            for asset in assets:
                loaded = unreal.EditorAssetLibrary.load_asset(asset)
                if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                    mesh_assets.append(loaded)
        else:
            # Assume it's a direct path to an asset
            loaded = unreal.EditorAssetLibrary.load_asset(asset_path)
            if isinstance(loaded, (unreal.StaticMesh, unreal.SkeletalMesh)):
                mesh_assets.append(loaded)

        if not mesh_assets:
            raise ValueError("No valid mesh assets found in provided paths.")

        unreal.log(f"{len(locations)}")
        unreal.log(f"{len(rotations)}")
        unreal.log(f"{len(scales)}")

        placed_actors = 0

        for i, (loc, rot, scale) in enumerate(zip(locations, rotations, scales)):
            mesh_asset = random.choice(mesh_assets)
            bounds = mesh_asset.get_bounding_box()
            max_dim = max(
                bounds.max.x - bounds.min.x,
                bounds.max.y - bounds.min.y,
                bounds.max.z - bounds.min.z,
            )
            scale_ = scale / max_dim * 100.0
            loc_v = unreal.Vector(*loc)
            rot_v = unreal.Rotator(0.0, 0.0, rot)
            scale_v = unreal.Vector(scale_, scale_, scale_)

            hit_results = unreal.SystemLibrary.line_trace_multi(
                unreal.EditorLevelLibrary.get_editor_world(),
                start=unreal.Vector(loc[0], loc[1], 2000),
                end=unreal.Vector(loc[0], loc[1], -2000),
                trace_channel=unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,  # Visibility
                trace_complex=False,
                actors_to_ignore=[],
                draw_debug_type=unreal.DrawDebugTrace.NONE,
                ignore_self=True,
            )
            if not hit_results or any(
                [
                    h.to_tuple()[9].get_class().get_name() != "Landscape"
                    for h in hit_results
                ]
            ):
                continue
            else:
                hit_result = hit_results[0].to_tuple()
                loc_v = hit_result[4]

            # Determine the actor class
            if isinstance(mesh_asset, unreal.StaticMesh):
                actor_class = unreal.StaticMeshActor
            elif isinstance(mesh_asset, unreal.SkeletalMesh):
                actor_class = unreal.SkeletalMeshActor
            else:
                raise TypeError("Unsupported mesh type.")

            # Spawn actor in the world
            actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
                actor_class, loc_v, rot_v
            )
            if not actor:
                raise RuntimeError("Failed to spawn actor.")
            actor.set_actor_label(f"{prefix_name}_{i}")

            actor.set_actor_scale3d(scale_v)

            # Set the mesh on the actor
            if isinstance(actor, unreal.StaticMeshActor):
                actor.static_mesh_component.set_static_mesh(mesh_asset)
            elif isinstance(actor, unreal.SkeletalMeshActor):
                actor.skeletal_mesh_component.set_skeletal_mesh(mesh_asset)

            placed_actors += 1

        return Responses.create_success_response(
            {"message": f"Placed {placed_actors} actors with prefix: {prefix_name}"}
        )
