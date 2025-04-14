#include "PythonExtension.h"
#include "IPythonScriptPlugin.h"
#include "Async/Async.h"
#include "Containers/Ticker.h"

void UPythonExtension::LaunchScriptOnGameThread(const FString& PythonCode)
{
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([PythonCode](float DeltaTime) {
        IPythonScriptPlugin::Get()->ExecPythonCommand(*PythonCode);
        return false; // don't repeat
    }), 0.1f);
}
