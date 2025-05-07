#include "Widgets/ChatBubbleWidget.h"

void UChatBubbleWidget::SetMessage(const FText& InText)
{
    if (MessageText)
    {
        MessageText->SetText(InText);
    }
}