#include "Widgets/MCPPythonButton.h"

void UMCPPythonButton::SynchronizeProperties()
{
    Super::SynchronizeProperties();
    OnClicked.Clear();
    OnClicked.AddDynamic(this, &UMCPPythonButton::HandleClick);
}

void UMCPPythonButton::HandleClick()
{
    OnClickedPython.Broadcast();
}

void UMCPPythonButton::SetButtonText(const FText& NewText)
{
    if (UWidget* content = GetChildAt(0))
    {
        if (UTextBlock* textBlock = Cast<UTextBlock>(content))
        {
            textBlock->SetText(NewText);
        }
    }
}
