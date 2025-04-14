import unreal
from typing import Any

from commands.utils import Responses, run_on_main_thread


class EditorCommands:

    @staticmethod
    @run_on_main_thread
    def import_asset(
        asset_path: str, asset_category: str | None = None
    ) -> dict[str, Any]:
        """
        Import an asset into Unreal Engine.
        Args:
            asset_path (str): The path to the asset to import.
            asset_category (str | None): Asset Category (can be anything eg. "Tree").
            If provided, the asset will be put in a subfolder with this name.
        """
        import_extension = unreal.Paths.get_extension(asset_path, False)

        is_gltf = import_extension == "glb" or import_extension == "gltf"

        is_fbx = import_extension == "fbx"

        if is_fbx:
            level_editor_subsystem = unreal.get_editor_subsystem(
                unreal.LevelEditorSubsystem
            )
            unreal.SystemLibrary.execute_console_command(
                level_editor_subsystem.get_world(),
                "Interchange.FeatureFlags.Import.FBX true",
            )

        editor_asset_subsystem = unreal.get_editor_subsystem(
            unreal.EditorAssetSubsystem
        )

        transient_path = "/Interchange/Pipelines/Transient/"
        transient_pipeline_path = transient_path + "MyAutomationPipeline"

        editor_asset_subsystem.delete_directory(transient_path)

        if is_gltf:
            pipeline = editor_asset_subsystem.duplicate_asset(
                "/Interchange/Pipelines/DefaultGLTFAssetsPipeline",
                transient_pipeline_path,
            )
        else:
            pipeline = editor_asset_subsystem.duplicate_asset(
                "/Interchange/Pipelines/DefaultAssetsPipeline",
                transient_pipeline_path,
            )

        # combine static mesh
        pipeline.mesh_pipeline.combine_static_meshes = True
        pipeline.material_pipeline.import_materials = True
        pipeline.material_pipeline.texture_pipeline.import_textures = True

        source_data = unreal.InterchangeManager.create_source_data(asset_path)
        import_asset_parameters = unreal.ImportAssetParameters()
        import_asset_parameters.is_automated = True

        import_asset_parameters.override_pipelines.append(
            unreal.SoftObjectPath(transient_pipeline_path + ".MyAutomationPipeline")
        )
        if is_gltf:
            import_asset_parameters.override_pipelines.append(
                unreal.SoftObjectPath("/Interchange/Pipelines/DefaultGLTFPipeline")
            )

        interchange_manager = (
            unreal.InterchangeManager.get_interchange_manager_scripted()
        )
        destination_path = "/Game/ImportedGLB/"
        if asset_category:
            destination_path += f"{asset_category}/"
        destination_path += unreal.Paths.get_base_filename(asset_path)
        success = interchange_manager.import_asset(
            destination_path, source_data, import_asset_parameters
        )
        if not success:
            raise Exception("Failed to import asset.")

        editor_asset_subsystem.delete_directory(transient_path)
        return Responses.create_success_response({"import_dest_path": destination_path})
