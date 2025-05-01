import unreal


def spawn_cube(location=unreal.Vector(0, 0, 0)):
    # Load the cube static mesh (default UE cube)
    cube_mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube")

    # Spawn an empty StaticMeshActor in the level
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(
        unreal.StaticMeshActor, location
    )

    # Set the static mesh to the cube
    static_mesh_comp = actor.static_mesh_component
    static_mesh_comp.set_static_mesh(cube_mesh)

    # Optional: update transform, collision, etc.
    static_mesh_comp.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    actor.set_actor_label("PythonCube")

    print("Cube spawned at", location)


spawn_cube()
