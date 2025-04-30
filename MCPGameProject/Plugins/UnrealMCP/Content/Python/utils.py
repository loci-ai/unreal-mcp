import emoji
import json
import markdown2

from bs4 import BeautifulSoup


def wrap_emojis_with_tag(text: str, tag: str = "emoji") -> str:
    emoji_entries = emoji.emoji_list(text)
    if not emoji_entries:
        return text

    result = []
    last_index = 0
    for entry in emoji_entries:
        start, end = entry["match_start"], entry["match_end"]
        result.append(text[last_index:start])
        result.append(f"<{tag}>{text[start:end]}</>")
        last_index = end

    result.append(text[last_index:])
    return "".join(result)


def json_pretty(obj) -> str:
    """
    Pretty print a JSON object.
    """
    try:
        if isinstance(obj, str):
            obj = json.loads(obj)
        return json.dumps(obj, indent=2)
    except TypeError:
        return str(obj)


def convert_markdown_to_richtext(md_text: str) -> str:
    md_text = wrap_emojis_with_tag(md_text)
    html = markdown2.markdown(
        md_text, extras=["fenced-code-blocks", "code-friendly", "break-on-newline"]
    )

    soup = BeautifulSoup(html, "html.parser")
    result_lines = []

    def process_list(tag, indent_level=0, ordered=False, index_start=1):
        index = index_start
        for li in tag.find_all("li", recursive=False):
            bullet = f"{index}." if ordered else "•"
            indent = "  " * indent_level

            immediate_parts = []
            nested_lists = []

            for child in li.contents:
                if getattr(child, "name", None) in ("ul", "ol"):
                    nested_lists.append(child)
                else:
                    if hasattr(child, "decode_contents"):
                        immediate_parts.append(child.decode_contents().strip())
                    else:
                        immediate_parts.append(str(child).strip())

            immediate_text = " ".join(immediate_parts).strip()
            if immediate_text:
                result_lines.append(f"{indent}{bullet} {immediate_text}")

            for nested_list in nested_lists:
                is_ordered = nested_list.name == "ol"
                process_list(nested_list, indent_level + 1, ordered=is_ordered)

            if ordered:
                index += 1

    for el in soup.contents:
        if el.name in {"h1", "h2", "h3"}:
            result_lines.append(f"<{el.name}>{el.get_text()}</>")
        elif el.name in ("ul", "ol"):
            process_list(el, ordered=(el.name == "ol"))
        elif el.name == "p":
            result_lines.append(f"\n{el.decode_contents().strip()}")
        elif el.name:
            result_lines.append(el.decode_contents().strip())
        else:
            result_lines.append(str(el).strip())

    cleaned = "\n".join(result_lines)

    replacements = [
        ("<strong>", "<b>"),
        ("</strong>", "</>"),
        ("<em>", "<i>"),
        ("</em>", "</>"),
        ("<code>", "<code>"),
        ("</code>", "</>"),
        ("<pre>", ""),
        ("</pre>", ""),
    ]
    for old, new in replacements:
        cleaned = cleaned.replace(old, new)
    return cleaned.strip()
