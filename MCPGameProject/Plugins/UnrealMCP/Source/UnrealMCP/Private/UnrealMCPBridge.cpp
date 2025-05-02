#include "UnrealMCPBridge.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "JsonObjectConverter.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Async/Async.h"
// Add Blueprint related includes
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "K2Node_Event.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SphereComponent.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
// UE5.5 correct includes
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"
#include "UObject/Field.h"
#include "UObject/FieldPath.h"
// Blueprint Graph specific includes
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_CallFunction.h"
#include "K2Node_InputAction.h"
#include "K2Node_Self.h"
#include "GameFramework/InputSettings.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
// Include our new command handler classes
#include "Commands/UnrealMCPActorCommands.h"
#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPBlueprintCommands.h"
#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"


// Initialize subsystem
void UUnrealMCPBridge::Initialize(FSubsystemCollectionBase& Collection)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Initializing"));
    // Create command handlers
    ActorCommands = MakeShared<FUnrealMCPActorCommands>();
    EditorCommands = MakeShared<FUnrealMCPEditorCommands>();
    BlueprintCommands = MakeShared<FUnrealMCPBlueprintCommands>();
    BlueprintNodeCommands = MakeShared<FUnrealMCPBlueprintNodeCommands>();
}

// Clean up resources when subsystem is destroyed
void UUnrealMCPBridge::Deinitialize()
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Shutting down"));
}

// Execute a command received from a client
FString UUnrealMCPBridge::ExecuteCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogTemp, Display, TEXT("UnrealMCPBridge: Executing command: %s"), *CommandType);
    
    TSharedPtr<FJsonObject> ResponseJson = MakeShareable(new FJsonObject);
    try
    {
        TSharedPtr<FJsonObject> ResultJson;
        
        if (CommandType == TEXT("ping"))
        {
            ResultJson = MakeShareable(new FJsonObject);
            ResultJson->SetStringField(TEXT("message"), TEXT("pong"));
        }
        // Actor Commands
        else if (CommandType == TEXT("get_actors_in_level") || 
                    CommandType == TEXT("find_actors_by_name") ||
                    CommandType == TEXT("create_actor") || 
                    CommandType == TEXT("delete_actor") || 
                    CommandType == TEXT("set_actor_transform") ||
                    CommandType == TEXT("get_actor_properties") ||
                    CommandType == TEXT("create_terrain"))
        {
            ResultJson = ActorCommands->HandleCommand(CommandType, Params);
        }
        // Editor Commands
        else if (CommandType == TEXT("focus_viewport") || 
                    CommandType == TEXT("take_screenshot") ||
                    CommandType == TEXT("view_asset"))
        {
            ResultJson = EditorCommands->HandleCommand(CommandType, Params);
        }
        // Blueprint Commands
        else if (CommandType == TEXT("create_blueprint") || 
                    CommandType == TEXT("add_component_to_blueprint") || 
                    CommandType == TEXT("set_component_property") || 
                    CommandType == TEXT("set_physics_properties") || 
                    CommandType == TEXT("compile_blueprint") || 
                    CommandType == TEXT("spawn_blueprint_actor") || 
                    CommandType == TEXT("set_blueprint_property") || 
                    CommandType == TEXT("set_static_mesh_properties") ||
                    CommandType == TEXT("set_pawn_properties"))
        {
            ResultJson = BlueprintCommands->HandleCommand(CommandType, Params);
        }
        // Blueprint Node Commands
        else if (CommandType == TEXT("connect_blueprint_nodes") || 
                    CommandType == TEXT("create_input_mapping") || 
                    CommandType == TEXT("add_blueprint_get_self_component_reference") ||
                    CommandType == TEXT("add_blueprint_self_reference") ||
                    CommandType == TEXT("find_blueprint_nodes") ||
                    CommandType == TEXT("add_blueprint_event_node") ||
                    CommandType == TEXT("add_blueprint_input_action_node") ||
                    CommandType == TEXT("add_blueprint_function_node") ||
                    CommandType == TEXT("add_blueprint_get_component_node") ||
                    CommandType == TEXT("add_blueprint_variable"))
        {
            ResultJson = BlueprintNodeCommands->HandleCommand(CommandType, Params);
        }
        else
        {
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
            
            FString ResultString;
            TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
            FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
            return ResultString;
        }
        
        // Check if the result contains an error
        bool bSuccess = true;
        FString ErrorMessage;
        
        if (ResultJson->HasField(TEXT("success")))
        {
            bSuccess = ResultJson->GetBoolField(TEXT("success"));
            if (!bSuccess && ResultJson->HasField(TEXT("error")))
            {
                ErrorMessage = ResultJson->GetStringField(TEXT("error"));
            }
        }
        
        if (bSuccess)
        {
            // Set success status and include the result
            ResponseJson->SetStringField(TEXT("status"), TEXT("success"));
            ResponseJson->SetObjectField(TEXT("result"), ResultJson);
        }
        else
        {
            // Set error status and include the error message
            ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
            ResponseJson->SetStringField(TEXT("error"), ErrorMessage);
        }
    }
    catch (const std::exception& e)
    {
        ResponseJson->SetStringField(TEXT("status"), TEXT("error"));
        ResponseJson->SetStringField(TEXT("error"), UTF8_TO_TCHAR(e.what()));
    }
    
    FString ResultString;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ResultString);
    FJsonSerializer::Serialize(ResponseJson.ToSharedRef(), Writer);
    return ResultString;
}

FString UUnrealMCPBridge::ExecuteCommandFromJson(const FString& CommandType, const FString& ParamsJson)
{
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ParamsJson);
    
    if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
    {
        return ExecuteCommand(CommandType, JsonObject);
    }

    TSharedPtr<FJsonObject> ErrorJson = MakeShareable(new FJsonObject);
    ErrorJson->SetStringField(TEXT("status"), TEXT("error"));
    ErrorJson->SetStringField(TEXT("error"), TEXT("Invalid JSON input"));

    FString ErrorResult;
    TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ErrorResult);
    FJsonSerializer::Serialize(ErrorJson.ToSharedRef(), Writer);
    return ErrorResult;
}


// For now, we'll keep the original command handler methods in place
// They'll be eventually removed once we've fully migrated all functionality to the handlers

// The original handler methods will be kept for the initial build test
TSharedPtr<FJsonObject> UUnrealMCPBridge::HandleActorCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // This is a temporary pass-through to the new ActorCommands handler
    return ActorCommands->HandleCommand(CommandType, Params);
}

TSharedPtr<FJsonObject> UUnrealMCPBridge::HandleEditorCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // This is a temporary pass-through to the new EditorCommands handler
    return EditorCommands->HandleCommand(CommandType, Params);
}

TSharedPtr<FJsonObject> UUnrealMCPBridge::HandleBlueprintCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // This is a temporary pass-through to the new BlueprintCommands handler
    return BlueprintCommands->HandleCommand(CommandType, Params);
}

TSharedPtr<FJsonObject> UUnrealMCPBridge::HandleBlueprintNodeCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // This is a temporary pass-through to the new BlueprintNodeCommands handler
    return BlueprintNodeCommands->HandleCommand(CommandType, Params);
}