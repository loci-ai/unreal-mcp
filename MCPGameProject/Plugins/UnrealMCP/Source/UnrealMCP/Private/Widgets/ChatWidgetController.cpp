#include "Widgets/ChatWidgetController.h"
#include "Blueprint/UserWidget.h"
#include "Widgets/ChatBubbleWidget.h"

UUserWidget* UChatWidgetController::CreateChatBubble(UWorld* WorldContext, TSubclassOf<UUserWidget> WidgetClass, const FText& Message)
{
    if (!WidgetClass || !WorldContext)
    {
        return nullptr;
    }

    UUserWidget* Widget = CreateWidget<UUserWidget>(WorldContext, WidgetClass);
    if (!Widget)
    {
        return nullptr;
    }

    if (UChatBubbleWidget* Bubble = Cast<UChatBubbleWidget>(Widget))
    {
        UE_LOG(LogTemp, Log, TEXT("Creating chat bubble"));
        Bubble->SetMessage(Message);
    }

    return Widget;
}
