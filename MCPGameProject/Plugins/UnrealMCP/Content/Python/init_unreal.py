import unreal

from loci_utils import setup_env_variables
from mcp_widget import register_editor_menu
from runner import GameThreadRunner  # noqa

setup_env_variables()

unreal.register_slate_post_tick_callback(GameThreadRunner.tick_callback)

register_editor_menu()
