#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/RichTextBlock.h"
#include "Components/HorizontalBox.h"
#include "ChatBubbleWidget.generated.h"

UCLASS()
class UNREALMCP_API UChatBubbleWidget : public UUserWidget
{
    GENERATED_BODY()

public:

    // Called from C++ or Python
    UFUNCTION(BlueprintCallable, Category = "Chat")
    void SetMessage(const FText& InText);

protected:

    UPROPERTY(meta = (BindWidget))
    URichTextBlock* MessageText;

    UPROPERTY(meta = (BindWidget))
    UHorizontalBox* RootLayout;
};
