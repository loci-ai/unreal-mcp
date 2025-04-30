#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "ChatWidgetController.generated.h"

UCLASS(BlueprintType)
class UNREALMCP_API UChatWidgetController : public UObject
{
    GENERATED_BODY()

public:

    UFUNCTION(BlueprintCallable, Category = "Chat")
    UUserWidget* CreateChatBubble(UWorld* WorldContext, TSubclassOf<UUserWidget> WidgetClass, const FText& Message);
};
