#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "PythonExtension.generated.h"

UCLASS(BlueprintType)
class UNREALMCP_API UPythonExtension : public UObject
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Python")
    static void LaunchScriptOnGameThread(const FString &PythonCode);

    UFUNCTION(BlueprintCallable, Category = "Python")
    static bool IsInGameThread();
};
