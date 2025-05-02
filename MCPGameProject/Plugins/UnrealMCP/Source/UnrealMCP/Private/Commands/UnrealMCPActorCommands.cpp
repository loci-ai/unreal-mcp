#include "Commands/UnrealMCPActorCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "Subsystems/EditorAssetSubsystem.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/SkeletalMeshActor.h"
#include "Engine/World.h"
#include "InterchangeManager.h"
#include "InterchangeSourceData.h"
#include "InterchangePipelineBase.h"
#include "InterchangeGenericAssetsPipeline.h"
#include "InterchangeGenericMeshPipeline.h"
#include "InterchangeGenericMaterialPipeline.h"
#include "InterchangeGenericTexturePipeline.h"
#include "Misc/Paths.h"
#include "EditorScriptingUtilities/Public/EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Misc/FileHelper.h"
#include "Landscape.h"
#include "LandscapeComponent.h"
#include "LandscapeEdit.h"
#include "LandscapeConfigHelper.h"
#include "UObject/SoftObjectPath.h"
#include "Containers/Ticker.h"


FUnrealMCPActorCommands::FUnrealMCPActorCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("get_actors_in_level"))
    {
        return HandleGetActorsInLevel(Params);
    }
    else if (CommandType == TEXT("find_actors_by_name"))
    {
        return HandleFindActorsByName(Params);
    }
    else if (CommandType == TEXT("create_actor"))
    {
        return HandleCreateActor(Params);
    }
    else if (CommandType == TEXT("delete_actor"))
    {
        return HandleDeleteActor(Params);
    }
    else if (CommandType == TEXT("set_actor_transform"))
    {
        return HandleSetActorTransform(Params);
    }
    else if (CommandType == TEXT("get_actor_properties"))
    {
        return HandleGetActorProperties(Params);
    }
    else if (CommandType == TEXT("create_terrain"))
    {
        return HandleCreateTerrain(Params);
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown actor command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleGetActorsInLevel(const TSharedPtr<FJsonObject>& Params)
{
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> ActorArray;
    for (AActor* Actor : AllActors)
    {
        if (Actor)
        {
            TSharedPtr<FJsonObject> ActorObject = MakeShared<FJsonObject>();
            ActorObject->SetStringField(TEXT("name"), Actor->GetActorLabel());
            ActorObject->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
            ActorArray.Add(MakeShared<FJsonValueObject>(ActorObject));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), ActorArray);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleFindActorsByName(const TSharedPtr<FJsonObject>& Params)
{
    FString Pattern;
    if (!Params->TryGetStringField(TEXT("pattern"), Pattern))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'pattern' parameter"));
    }
    
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> MatchingActors;
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName().Contains(Pattern))
        {
            MatchingActors.Add(FUnrealMCPCommonUtils::ActorToJson(Actor));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), MatchingActors);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleCreateActor(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString ActorType;
    if (!Params->TryGetStringField(TEXT("type"), ActorType))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'type' parameter"));
    }

    // Get actor name (required parameter)
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Get optional transform parameters
    FVector Location(0.0f, 0.0f, 0.0f);
    FRotator Rotation(0.0f, 0.0f, 0.0f);
    FVector Scale(1.0f, 1.0f, 1.0f);

    if (Params->HasField(TEXT("location")))
    {
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        Rotation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"));
    }
    if (Params->HasField(TEXT("scale")))
    {
        Scale = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale"));
    }

    // Create the actor based on type
    AActor* NewActor = nullptr;
    UWorld* World = GEditor->GetEditorWorldContext().World();

    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Check if an actor with this name already exists
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetActorLabel() == ActorName)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor with name '%s' already exists"), *ActorName));
        }
    }

    FActorSpawnParameters SpawnParams;

    if (ActorType == TEXT("StaticMeshActor"))
    {
        NewActor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("PointLight"))
    {
        NewActor = World->SpawnActor<APointLight>(APointLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("SpotLight"))
    {
        NewActor = World->SpawnActor<ASpotLight>(ASpotLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("DirectionalLight"))
    {
        NewActor = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorType == TEXT("CameraActor"))
    {
        NewActor = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Location, Rotation, SpawnParams);
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown actor type: %s"), *ActorType));
    }

    if (NewActor)
    {
        // Set scale (since SpawnActor only takes location and rotation)
        FTransform Transform = NewActor->GetTransform();
        Transform.SetScale3D(Scale);
        NewActor->SetActorTransform(Transform);
        NewActor->SetActorLabel(ActorName);

        // Return the created actor's details
        return FUnrealMCPCommonUtils::ActorToJsonObject(NewActor, true);
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create actor"));
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleDeleteActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetActorLabel() == ActorName)
        {
            // Store actor info before deletion for the response
            TSharedPtr<FJsonObject> ActorInfo = FUnrealMCPCommonUtils::ActorToJsonObject(Actor);
            
            // Delete the actor
            Actor->Destroy();
            
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetObjectField(TEXT("deleted_actor"), ActorInfo);
            return ResultObj;
        }
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params)
{
    // Get actor name
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetActorLabel() == ActorName)
        {
            TargetActor = Actor;
            break;
        }
    }

    if (!TargetActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Get transform parameters
    FTransform NewTransform = TargetActor->GetTransform();

    if (Params->HasField(TEXT("location")))
    {
        NewTransform.SetLocation(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location")));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        NewTransform.SetRotation(FQuat(FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"))));
    }
    if (Params->HasField(TEXT("scale")))
    {
        NewTransform.SetScale3D(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale")));
    }

    // Set the new transform
    TargetActor->SetActorTransform(NewTransform);

    // Return updated actor info
    return FUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleGetActorProperties(const TSharedPtr<FJsonObject>& Params)
{
    // Get actor name
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            TargetActor = Actor;
            break;
        }
    }

    if (!TargetActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Always return detailed properties for this command
    return FUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

bool LoadRawHeightmapR16(const FString& FilePath, TArray<uint16>& OutHeightData)
{
    TArray<uint8> RawBytes;
    if (!FFileHelper::LoadFileToArray(RawBytes, *FilePath))
    {
        UE_LOG(LogTemp, Error, TEXT("❌ Failed to load .r16 heightmap: %s"), *FilePath);
        return false;
    }
    int32 Width = 1009;
    int32 Height = 1009;

    int32 ExpectedSize = Width * Height * sizeof(uint16);
    if (RawBytes.Num() != ExpectedSize)
    {
        UE_LOG(LogTemp, Error, TEXT("❌ Size mismatch: expected %d bytes, got %d"), ExpectedSize, RawBytes.Num());
        return false;
    }

    OutHeightData.SetNumUninitialized(Width * Height);
    FMemory::Memcpy(OutHeightData.GetData(), RawBytes.GetData(), ExpectedSize);
    return true;
}

TSharedPtr<FJsonObject> FUnrealMCPActorCommands::HandleCreateTerrain(const TSharedPtr<FJsonObject>& Params)
{
    FString HeightMapPath;
    if (!Params->TryGetStringField(TEXT("heightmap_path"), HeightMapPath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'heightmap_path' parameter"));
    }

    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    TArray<uint16> HeightData;
    if (!LoadRawHeightmapR16(HeightMapPath, HeightData))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to load heightmap data"));
    }

    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Setup landscape params (matching the working example)
    const int32 SectionSize = 63; // This is QuadsPerSection
    const int32 SectionsPerComponent = 1;
    const int32 ComponentCountX = 16;
    const int32 ComponentCountY = 16;
    const int32 QuadsPerComponent = SectionSize * SectionsPerComponent;

    // Calculate dimensions
    int32 SizeX = ComponentCountX * QuadsPerComponent + 1;
    int32 SizeY = ComponentCountY * QuadsPerComponent + 1;

    // Prepare material layers (empty in this case)
    TArray<FLandscapeImportLayerInfo> MaterialImportLayers;
    MaterialImportLayers.Reserve(0);

    // Create data containers
    TMap<FGuid, TArray<uint16>> HeightDataPerLayers;
    TMap<FGuid, TArray<FLandscapeImportLayerInfo>> MaterialLayerDataPerLayers;

    // Add the height data to the map with a blank GUID
    HeightDataPerLayers.Add(FGuid(), MoveTemp(HeightData));
    
    // Add empty material layers with blank GUID
    MaterialLayerDataPerLayers.Add(FGuid(), MoveTemp(MaterialImportLayers));

    // Spawn the landscape actor
    ALandscape* Landscape = World->SpawnActor<ALandscape>();
    if (!Landscape)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn landscape actor"));
    }

    // Set up landscape properties
    Landscape->bCanHaveLayersContent = false;
    Landscape->LandscapeMaterial = nullptr;
    Landscape->SetActorLabel(*ActorName);

    // Set transform - position at origin with scale
    FTransform LandscapeTransform = FTransform::Identity;
    LandscapeTransform.SetLocation(FVector(0.0f, 0.0f, 0.0f));
    LandscapeTransform.SetScale3D(FVector(1.0f, 1.0f, 1.0f));
    Landscape->SetActorTransform(LandscapeTransform);

    // Import the height data into the landscape
    Landscape->Import(
        FGuid::NewGuid(), 
        0, 0, 
        SizeX - 1, SizeY - 1,
        SectionsPerComponent,
        QuadsPerComponent, 
        HeightDataPerLayers, 
        nullptr,
        MaterialLayerDataPerLayers, 
        ELandscapeImportAlphamapType::Additive
    );

    // Calculate and set static lighting LOD
    Landscape->StaticLightingLOD = FMath::DivideAndRoundUp(FMath::CeilLogTwo((SizeX * SizeY) / (2048 * 2048) + 1), (uint32)2);
    
    // Update landscape info
    float ComponentSizeUU = QuadsPerComponent * 100.0f * Landscape->GetActorScale().X; // Assuming uniform scale
    int32 WorldPartitionGridSize = FMath::RoundToInt(ComponentSizeUU);

    ULandscapeInfo* LandscapeInfo = Landscape->GetLandscapeInfo();
    if (LandscapeInfo)
    {
        LandscapeInfo->UpdateLayerInfoMap(Landscape);
        // Setup World Partition streaming proxies (if applicable)
        ULandscapeSubsystem* LandscapeSubsystem = World->GetSubsystem<ULandscapeSubsystem>();
        if (LandscapeSubsystem && World->GetWorldPartition())
        {
            LandscapeSubsystem->ChangeGridSize(LandscapeInfo, WorldPartitionGridSize);
        }
    }

    // Register components and finalize
    Landscape->RegisterAllComponents();

    // Update material properties
    FPropertyChangedEvent MaterialPropertyChangedEvent(FindFieldChecked<FProperty>(Landscape->GetClass(), FName("LandscapeMaterial")));
    Landscape->PostEditChangeProperty(MaterialPropertyChangedEvent);
    Landscape->PostEditChange();

    return FUnrealMCPCommonUtils::ActorToJsonObject(Landscape, true);

    

    return FUnrealMCPCommonUtils::ActorToJsonObject(Landscape, true);
}
