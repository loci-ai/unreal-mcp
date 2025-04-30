#pragma once

#include "CoreMinimal.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "MCPPythonButton.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnClickedPython);

UCLASS(Blueprintable, BlueprintType, meta = (DisplayName = "MCP Python Button"))
class UNREALMCP_API UMCPPythonButton : public UButton
{
    GENERATED_BODY()

public:
    // Python-callable delegate
    UPROPERTY(BlueprintAssignable, Category = "Events")
    FOnClickedPython OnClickedPython;

    // Set label text on the button's child TextBlock
    UFUNCTION(BlueprintCallable, Category = "UI")
    void SetButtonText(const FText& NewText);

protected:
    virtual void SynchronizeProperties() override;

private:
    UFUNCTION()
    void HandleClick();
};
