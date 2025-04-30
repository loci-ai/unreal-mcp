import asyncio
import json
import re
import threading
import unreal


from agents import Agent, Runner
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseTextDeltaEvent,
)

from mcp_server import create_mcp_server
from runner import GameThreadRunner
from utils import convert_markdown_to_richtext, json_pretty


class MCPChatWidget:
    CURRENT_TAB_ID = None

    def __init__(self, widget):
        self.widget = widget
        self.message_history = []
        self.is_cancel_requested = False
        self.current_thread = None
        self.current_runner = None
        self.current_llm_text = ""
        self.current_llm_block = None
        self.current_throbber = None
        self.code_block_class = None
        self.chat_controller = unreal.ChatWidgetController()

        self.setup_ui()
        self.setup_agent()

    def setup_ui(self):
        submit_button = self.get_widget("SubmitButton")
        cancel_button = self.get_widget("CancelButton")
        new_chat_button = self.get_widget("NewChatButton")

        on_click_submit = submit_button.get_editor_property("OnClickedPython")
        on_click_submit.clear()
        on_click_submit.add_callable(self.on_submit_clicked)

        on_click_cancel = cancel_button.get_editor_property("OnClickedPython")
        on_click_cancel.clear()
        on_click_cancel.add_callable(self.on_cancel_clicked)

        on_click_new_chat = new_chat_button.get_editor_property("OnClickedPython")
        on_click_new_chat.clear()
        on_click_new_chat.add_callable(self.on_new_chat_clicked)

        submit_button.set_button_text("Submit")
        cancel_button.set_button_text("Stop Generation")
        new_chat_button.set_button_text("New Chat")

        self.style_set = unreal.load_object(
            None, "/UnrealMCP/Widgets/DT_ChatRichTextStyles.DT_ChatRichTextStyles"
        )

    def setup_agent(self):
        self.mcp_server = create_mcp_server()
        self.agent = Agent(
            name="UnrealMCPAgent",
            instructions="You are a helpful unreal editor assistant.",
            mcp_servers=[self.mcp_server],
        )

    @classmethod
    def spawn_mcp_widget(cls):
        if cls.CURRENT_TAB_ID and unreal.EditorUtilitySubsystem().does_tab_exist(
            cls.CURRENT_TAB_ID
        ):
            return
        unreal.log("Launching MCP Chat Assistant UI..")
        widget_asset = unreal.load_asset("/UnrealMCP/Widgets/MCPChatWidget")
        (
            widget,
            tab_id,
        ) = unreal.EditorUtilitySubsystem().spawn_and_register_tab_and_get_id(
            widget_asset
        )
        unreal.log("MCP Chat Assistant UI launched")
        cls(widget)
        cls.CURRENT_TAB_ID = tab_id

    def get_widget(self, name: str):
        return self.widget.get_editor_property(name)

    @GameThreadRunner.run_on_main_thread
    def add_user_bubble(self, message: str):
        bubble_class = unreal.load_class(
            None, "/UnrealMCP/Widgets/BP_ChatBubble.BP_ChatBubble_C"
        )
        editor_world = unreal.EditorLevelLibrary.get_editor_world()
        formatted = convert_markdown_to_richtext(message)
        bubble = self.chat_controller.create_chat_bubble(
            editor_world, bubble_class, unreal.Text(formatted)
        )
        if bubble:
            self.get_widget("ChatScrollBox").add_child(bubble)
            self.get_widget("ChatScrollBox").scroll_to_end()

    def add_code_block(self, code_str: str):
        try:
            code_obj = json.loads(code_str)
            code_str = json.dumps(code_obj, indent=2)
        except json.JSONDecodeError:
            pass

        @GameThreadRunner.run_on_main_thread
        def update():
            if not self.code_block_class:
                self.code_block_class = unreal.load_class(
                    None, "/UnrealMCP/Widgets/BP_CodeBlock.BP_CodeBlock_C"
                )
            editor_world = unreal.EditorLevelLibrary.get_editor_world()
            widget = self.chat_controller.create_chat_bubble(
                editor_world, self.code_block_class, unreal.Text(code_str)
            )
            self.get_widget("ChatScrollBox").add_child(widget)
            self.get_widget("ChatScrollBox").scroll_to_end()

        update()

    def split_and_render_markdown(self, raw_markdown: str):
        unreal.log(raw_markdown)
        pattern = r"```([\w\W]*)\n(.*?)\n?```"
        spans = []
        for match in re.finditer(pattern, raw_markdown, re.DOTALL):
            start, end = match.span()
            spans.append((start, end))
        cur_index = 0
        new_block = False
        for start, end in spans:
            if cur_index < start:
                text = raw_markdown[cur_index:start].strip()
                if new_block:
                    self.new_llm_output(text)
                    new_block = False
                else:
                    self.current_llm_text += text
                    self.update_llm_output(self.current_llm_text)
            code_block = raw_markdown[start + 3 : end - 3]  # Remove backticks
            parts = code_block.split("\n", maxsplit=1)
            self.add_code_block(parts[1])
            cur_index = end
            new_block = True
        if cur_index < len(raw_markdown):
            text = raw_markdown[cur_index:].strip()
            if new_block:
                self.new_llm_output(text)
            else:
                self.current_llm_text += text
                self.update_llm_output(text)

    def on_submit_clicked(self):
        unreal.log("Submit clicked")
        prompt = str(self.get_widget("PromptInputBox").get_text())
        if not prompt.strip():
            return
        self.add_user_bubble(prompt)
        self.message_history.append(EasyInputMessageParam(role="user", content=prompt))
        self.run_prompt()

    @GameThreadRunner.run_on_main_thread
    def on_new_chat_clicked(self):
        unreal.log("New chat clicked")
        self.message_history = []
        self.current_throbber = None
        self.current_llm_text = ""
        self.current_llm_block = None
        self.is_cancel_requested = False
        self.get_widget("ChatScrollBox").clear_children()
        self.set_thinking(False)

    def on_cancel_clicked(self):
        unreal.log("Cancel clicked")
        self.is_cancel_requested = True
        self.new_llm_output("Canceling generation...")

    @GameThreadRunner.run_on_main_thread
    def create_llm_text_block(self):
        self.remove_throbber()
        block = unreal.RichTextBlock()
        block.set_text_style_set(self.style_set)
        block.set_auto_wrap_text(True)

        border = unreal.Border()
        border.set_padding(unreal.Margin(24.0, 12.0, 24.0, 12.0))
        border.set_brush_color(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
        border.set_content(block)

        self.get_widget("ChatScrollBox").add_child(border)
        self.get_widget("ChatScrollBox").scroll_to_end()
        self.current_llm_block = block

    @GameThreadRunner.run_on_main_thread
    def set_thinking(self, is_thinking: bool):
        text = "Generating..." if is_thinking else "Submit your prompt here..."
        self.get_widget("PromptInputBox").set_hint_text(text)
        self.get_widget("PromptInputBox").set_text("")

    def new_llm_output(self, text: str):
        self.current_llm_text = text
        self.current_llm_block = None
        self.update_llm_output(text)

    def update_llm_output(self, new_text: str):
        formatted = convert_markdown_to_richtext(new_text)

        @GameThreadRunner.run_on_main_thread
        def update():
            if not self.current_llm_block:
                self.create_llm_text_block()
            self.current_llm_block.set_text(unreal.Text(formatted))

        update()

    @GameThreadRunner.run_on_main_thread
    def start_thinking_placeholder(self):
        throbber = unreal.Throbber()
        throbber.set_number_of_pieces(4)
        throbber.set_animate_vertically(False)
        throbber.set_animate_horizontally(True)
        throbber.set_animate_opacity(True)

        border = unreal.Border()
        border.set_padding(unreal.Margin(20.0, 12.0, 20.0, 12.0))
        border.set_brush_color(unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
        border.set_content(throbber)

        self.get_widget("ChatScrollBox").add_child(border)
        self.get_widget("ChatScrollBox").scroll_to_end()

        self.current_throbber = border

    @GameThreadRunner.run_on_main_thread
    def remove_throbber(self):
        if self.current_throbber:
            self.get_widget("ChatScrollBox").remove_child(self.current_throbber)
        self.current_throbber = None

    def run_prompt(self):
        async def task():
            self.current_llm_text = ""
            self.current_llm_block = None
            self.set_thinking(True)
            self.start_thinking_placeholder()

            self.current_runner = Runner.run_streamed(
                self.agent, input=self.message_history
            )

            try:
                async for event in self.current_runner.stream_events():
                    if self.is_cancel_requested:
                        self.new_llm_output("Generation canceled...")
                        break
                    if event.type == "raw_response_event" and isinstance(
                        event.data, ResponseTextDeltaEvent
                    ):
                        self.current_llm_text += event.data.delta
                        self.update_llm_output(self.current_llm_text)
                    elif event.type == "run_item_stream_event":
                        if event.item.type == "tool_call_item":
                            tool_call = event.item.to_input_item()
                            self.add_code_block(
                                f"# Tool Call: {tool_call['name']}\n{json_pretty(tool_call['arguments'])}"
                            )
                            self.message_history.append(tool_call)
                        elif event.item.type == "tool_call_output_item":
                            tool_call = event.item.to_input_item()
                            output = json.loads(tool_call["output"])
                            if "text" in output:
                                output = output["text"]
                            self.add_code_block(
                                f"# Tool Result:\n{json_pretty(output)}"
                            )
                            self.message_history.append(tool_call)
                        elif event.item.type == "message_output_item":
                            unreal.log(f"Message output item: {event.item.type}")
                            message = event.item.to_input_item()
                            self.split_and_render_markdown(self.current_llm_text)
                            self.current_llm_text = ""
                            self.current_llm_block = None
                            self.message_history.append(message)
            except Exception as e:
                self.new_llm_output(f"Generation error: {e}")
            finally:
                self.set_thinking(False)
                self.current_llm_block = None
                self.current_llm_text = ""

        def runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(task())
            loop.close()
            self.setup_ui()  # Ensure buttons don't become unbound
            self.log_widget_status()

        self.is_cancel_requested = False
        self.current_thread = threading.Thread(target=runner)
        self.current_thread.start()

    @GameThreadRunner.run_on_main_thread
    def log_widget_status(self):
        widget = self.widget
        submit = self.get_widget("SubmitButton")
        unreal.log_warning(f"Widget valid: {widget is not None}")
        unreal.log_warning(f"Submit button valid: {submit is not None}")
        unreal.log_warning(f"Submit button is enabled: {submit.is_enabled}")
        unreal.log_warning(
            f"Submit button handlers: {submit.get_editor_property('OnClickedPython')}"
        )


def register_editor_menu():
    menus = unreal.ToolMenus.get()
    menu = menus.find_menu("LevelEditor.MainMenu.Tools")

    if not menu:
        unreal.log_error("Could not find 'Tools' menu")
        return

    entry = unreal.ToolMenuEntry(
        name="MCPChatEntry",
        type=unreal.MultiBlockType.MENU_ENTRY,
        insert_position=unreal.ToolMenuInsert("", unreal.ToolMenuInsertType.DEFAULT),
    )
    entry.set_label("MCP Chat Assistant")
    entry.set_tool_tip("Launch the MCP chat assistant UI")
    entry.set_string_command(
        type=unreal.ToolMenuStringCommandType.PYTHON,
        custom_type="",
        string="from mcp_widget import MCPChatWidget; MCPChatWidget.spawn_mcp_widget()",
    )

    menu.add_menu_entry("MCPChatSection", entry)
    menus.refresh_all_widgets()
