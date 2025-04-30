#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Editor.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "ImageUtils.h"
#include "HighResScreenshot.h"
#include "Engine/GameViewportClient.h"
#include "Misc/FileHelper.h"

#include "ToolMenus.h"
#include "UObject/SoftObjectPath.h"

#if WITH_EDITOR
#include "Subsystems/AssetEditorSubsystem.h"
#endif

FUnrealMCPEditorCommands::FUnrealMCPEditorCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("focus_viewport"))
    {
        return HandleFocusViewport(Params);
    }
    else if (CommandType == TEXT("view_image"))
    {
        return HandleViewImage(Params);
    }
    else if (CommandType == TEXT("take_screenshot"))
    {
        return HandleTakeScreenshot(Params);
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown editor command: %s"), *CommandType));
}


TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleViewImage(const TSharedPtr<FJsonObject>& Params)
{
    FString ImagePath;
    if (!Params->TryGetStringField(TEXT("image_path"), ImagePath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'image_path' parameter"));
    }
    FSoftObjectPath SoftPath(ImagePath);
    UE_LOG(LogTemp, Display, TEXT("Successfull FSoftObjectPath SoftPath(ImagePath"));

    UObject* Image = SoftPath.TryLoad();
    UE_LOG(LogTemp, Display, TEXT("Successfull UObject* Image = SoftPath.TryLoad()"));

    if (Image && GEditor)
    {
        if (UAssetEditorSubsystem* EditorSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem>())
        {
            UE_LOG(LogTemp, Display, TEXT("Success UAssetEditorSubsystem* EditorSubsystem = GEditor->GetEditorSubsystem<UAssetEditorSubsystem"));
            
            EditorSubsystem->OpenEditorForAsset(ImagePath);
        }

        UE_LOG(LogTemp, Display, TEXT("Big ol success"));

        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("image_viewed"), true);
        return ResultObj;
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to view image"));
}


TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleFocusViewport(const TSharedPtr<FJsonObject>& Params)
{
    if (GEditor && GEditor->GetActiveViewport())
    {
        FLevelEditorViewportClient* ViewportClient = static_cast<FLevelEditorViewportClient*>(GEditor->GetActiveViewport()->GetClient());
        if (ViewportClient)
        {
            ViewportClient->FocusViewportOnBox(FBox(FVector(-100, -100, -100), FVector(100, 100, 100)));
            
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetBoolField(TEXT("focused"), true);
            return ResultObj;
        }
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to focus viewport"));
}


TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleTakeScreenshot(const TSharedPtr<FJsonObject>& Params)
{
    FString FilePath;
    if (!Params->TryGetStringField(TEXT("filepath"), FilePath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'filepath' parameter"));
    }
    
    if (GEditor && GEditor->GetActiveViewport())
    {
        FViewport* Viewport = GEditor->GetActiveViewport();
        TArray<FColor> Bitmap;
        FIntRect ViewportRect(0, 0, Viewport->GetSizeXY().X, Viewport->GetSizeXY().Y);
        
        if (Viewport->ReadPixels(Bitmap, FReadSurfaceDataFlags(), ViewportRect))
        {
            TArray<uint8> CompressedBitmap;
            FImageUtils::CompressImageArray(Viewport->GetSizeXY().X, Viewport->GetSizeXY().Y, Bitmap, CompressedBitmap);
            
            if (FFileHelper::SaveArrayToFile(CompressedBitmap, *FilePath))
            {
                TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
                ResultObj->SetStringField(TEXT("filepath"), FilePath);
                return ResultObj;
            }
        }
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to take screenshot"));
} 