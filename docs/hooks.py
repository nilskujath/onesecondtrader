import re
from pathlib import Path


def parse_sql_schema(sql_content: str) -> dict:
    lines = sql_content.strip().split("\n")

    module_docstring_lines = []
    blocks = []
    current_comment_lines = []
    current_sql_lines = []
    in_module_docstring = True
    in_block = False

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            if in_module_docstring:
                in_module_docstring = False
            continue

        if stripped.startswith("--"):
            comment_text = stripped[2:].strip()
            if in_module_docstring:
                module_docstring_lines.append(comment_text)
            else:
                current_comment_lines.append(comment_text)
        elif stripped.upper().startswith("CREATE"):
            in_module_docstring = False
            in_block = True
            current_sql_lines.append(line)
            if stripped.endswith(";"):
                blocks.append(
                    {
                        "docstring": "\n".join(current_comment_lines),
                        "sql": "\n".join(current_sql_lines),
                    }
                )
                current_comment_lines = []
                current_sql_lines = []
                in_block = False
        elif in_block:
            current_sql_lines.append(line)
            if stripped.endswith(";"):
                blocks.append(
                    {
                        "docstring": "\n".join(current_comment_lines),
                        "sql": "\n".join(current_sql_lines),
                    }
                )
                current_comment_lines = []
                current_sql_lines = []
                in_block = False

    return {"module_docstring": "\n".join(module_docstring_lines), "blocks": blocks}


ABBREVIATIONS = {"mbo", "bbo", "ohlcv", "mbp10", "ib", "mt5", "csv"}


def format_heading(name: str) -> str:
    if name.lower() in ABBREVIATIONS:
        return name.upper()
    return name.capitalize()


def format_title(name: str) -> str:
    words = name.replace("_", " ").split()
    return " ".join(
        w.upper() if w.lower() in ABBREVIATIONS else w.capitalize() for w in words
    )


def extract_block_name(sql: str) -> str:
    match = re.search(
        r"CREATE\s+(?:TABLE|INDEX|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        sql,
        re.IGNORECASE,
    )
    if match:
        return match.group(1)
    return "Unknown"


def generate_markdown(parsed: dict, title: str = "Schema") -> str:
    lines = [f"# {title}\n"]

    if parsed["module_docstring"]:
        lines.append(parsed["module_docstring"])
        lines.append("\n")

    for block in parsed["blocks"]:
        name = extract_block_name(block["sql"])
        heading = format_heading(name)
        lines.append(f"## {heading}\n")

        if block["docstring"]:
            lines.append(block["docstring"])
            lines.append("\n")

        lines.append("```sql")
        lines.append(block["sql"])
        lines.append("```\n")

    return "\n".join(lines)


def on_pre_build(config, **kwargs):
    src_root = Path("src/onesecondtrader")
    docs_root = Path("docs/reference")

    for sql_path in src_root.rglob("*.sql"):
        relative = sql_path.relative_to(src_root)
        output_path = docs_root / relative.with_suffix(".md")
        title = format_title(sql_path.stem)

        sql_content = sql_path.read_text()
        parsed = parse_sql_schema(sql_content)
        markdown = generate_markdown(parsed, title)

        if output_path.exists() and output_path.read_text() == markdown:
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown)
