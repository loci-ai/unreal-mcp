
import unreal


actors = unreal.EditorActorSubsystem().get_all_level_actors()
print(actors[0])