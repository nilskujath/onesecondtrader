#!/usr/bin/env python3
import logging
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "docs"))
from hooks import parse_sql_schema, generate_markdown  # type: ignore[import-not-found]

# SETUP LOGGER
# --------------------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# REFERENCE DOCUMENTATION GENERATION
# --------------------------------------------------------------------------------------


def format_module_title(module_name: str) -> str:
    """Format module name into a proper title with correct capitalization.

    Handles special cases:
    - 'ib', 'mt5', or 'csv' followed by or after an underscore becomes 'IB', 'MT5', or 'CSV'
    - Regular title case for other words

    Args:
        module_name: The module name to format (e.g., 'ib_broker', 'mt5_adapter', 'csv_parser')

    Returns:
        Formatted title (e.g., 'IB Broker', 'MT5 Adapter', 'CSV Parser')
    """
    # Replace underscores with spaces and apply title case
    title = module_name.replace("_", " ").title()

    # Fix specific capitalizations
    title = title.replace(" Ib ", " IB ").replace(" Ib", " IB")
    title = title.replace("Ib ", "IB ").replace("Ib", "IB")
    title = title.replace(" Mt5 ", " MT5 ").replace(" Mt5", " MT5")
    title = title.replace("Mt5 ", "MT5 ").replace("Mt5", "MT5")
    title = title.replace(" Csv ", " CSV ").replace(" Csv", " CSV")
    title = title.replace("Csv ", "CSV ").replace("Csv", "CSV")

    return title


def discover_package_structure(package_dir: Path, module_prefix: str) -> dict:
    """Recursively discover package structure to arbitrary depth.

    Args:
        package_dir: Path to the package directory
        module_prefix: Python module prefix (e.g., 'onesecondtrader.events')

    Returns:
        Dictionary with 'files' (list of .py file stems) and 'subpackages' (nested dict)
    """
    structure = {"files": [], "subpackages": {}}

    for py_file in package_dir.glob("*.py"):
        if py_file.name != "__init__.py":
            structure["files"].append(py_file.stem)

    for subdir in package_dir.iterdir():
        if subdir.is_dir() and (subdir / "__init__.py").exists():
            subpackage_name = subdir.name
            subpackage_prefix = f"{module_prefix}.{subpackage_name}"
            structure["subpackages"][subpackage_name] = discover_package_structure(
                subdir, subpackage_prefix
            )

    return structure


def generate_docs_recursive(
    package_dir: Path,
    docs_dir: Path,
    module_prefix: str,
    structure: dict,
):
    """Recursively generate documentation for a package and its subpackages.

    Args:
        package_dir: Path to the package directory
        docs_dir: Path to the docs output directory for this package
        module_prefix: Python module prefix (e.g., 'onesecondtrader.events')
        structure: Package structure dict from discover_package_structure
    """
    docs_dir.mkdir(parents=True, exist_ok=True)

    for file_stem in structure["files"]:
        file_title = format_module_title(file_stem)
        file_path = package_dir / f"{file_stem}.py"
        file_content = file_path.read_text()

        has_classes_or_functions = "def " in file_content or "class " in file_content

        if has_classes_or_functions:
            md_content = f"""# {file_title}

::: {module_prefix}.{file_stem}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
        else:
            indented_content = "\n".join(
                "    " + line for line in file_content.split("\n")
            )
            md_content = f"""# {file_title}

::: {module_prefix}.{file_stem}
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

???+ quote "Source code in `{file_stem}.py`"

    ```python linenums="1"
{indented_content}
    ```
"""

        md_file = docs_dir / f"{file_stem}.md"
        md_file.write_text(md_content)

    for subpackage_name, subpackage_structure in structure["subpackages"].items():
        subpackage_dir = package_dir / subpackage_name
        subpackage_docs_dir = docs_dir / subpackage_name
        subpackage_prefix = f"{module_prefix}.{subpackage_name}"
        generate_docs_recursive(
            subpackage_dir, subpackage_docs_dir, subpackage_prefix, subpackage_structure
        )


def build_nav_recursive(structure: dict, docs_prefix: str) -> list:
    """Recursively build navigation structure for mkdocs.yml.

    Args:
        structure: Package structure dict from discover_package_structure
        docs_prefix: Docs path prefix (e.g., 'reference/events')

    Returns:
        List of navigation items for mkdocs.yml
    """
    nav_items = []

    for file_stem in sorted(structure["files"]):
        file_title = format_module_title(file_stem)
        nav_items.append({file_title: f"{docs_prefix}/{file_stem}.md"})

    for subpackage_name in sorted(structure["subpackages"].keys()):
        subpackage_structure = structure["subpackages"][subpackage_name]
        subpackage_title = format_module_title(subpackage_name)
        subpackage_docs_prefix = f"{docs_prefix}/{subpackage_name}"
        subpackage_nav = build_nav_recursive(
            subpackage_structure, subpackage_docs_prefix
        )
        if subpackage_nav:
            nav_items.append({subpackage_title: subpackage_nav})

    return nav_items


def generate_reference_docs():
    """Generate reference documentation from docstrings via mkdocstrings package.

    Automatically discovers Python modules and submodules in src/onesecondtrader and generates
    corresponding markdown documentation files. Handles both:
    - Top-level .py files (like monitoring.py)
    - Submodule structure (like domain/ with __init__.py) to arbitrary nesting depth

    Modules with substantial content use mkdocstrings for automatic API documentation, while
    simple modules display their source code directly. This is done in the following steps:

        1. Clean and recreate docs/reference directory
        2. Recursively discover all Python modules and submodules (excluding __init__.py)
        3. Generate individual module documentation pages
        4. Create overview page with navigation cards
        5. Update mkdocs.yml navigation structure with hierarchical organization

    Submodules are always processed with mkdocstrings since they typically contain substantial
    content. Regular .py files are analyzed for content complexity.

    Output:
        - Individual .md files for each module/submodule in docs/reference/
        - Overview page at docs/reference/overview.md with correct file type indicators
        - Updated navigation in mkdocs.yml with proper module/submodule organization

    Raises:
        FileNotFoundError: If not run from project root directory.

    Note:
        This script must be run from the project root directory.
    """
    logger.info("Starting to generate reference documentation...")

    # VALIDATE THAT WE'RE IN THE PROJECT ROOT DIRECTORY
    # ----------------------------------------------------------------------------------

    src_path = Path("src/onesecondtrader")
    mkdocs_path = Path("mkdocs.yml")

    if not src_path.exists() or not mkdocs_path.exists():
        logger.error("Script must be run from the project root directory.")
        raise FileNotFoundError("Script must be run from the project root directory. ")

    # CLEAN AND RECREATE REFERENCE DOCS DIRECTORY
    # ----------------------------------------------------------------------------------

    docs_path = Path("docs/reference")
    if docs_path.exists():
        shutil.rmtree(docs_path)
        logger.info(f"Cleaned existing documentation directory: {docs_path}")
    docs_path.mkdir(parents=True, exist_ok=True)

    # GENERATE SCHEMA DOCUMENTATION FROM SQL
    # ----------------------------------------------------------------------------------

    sql_path = Path("src/onesecondtrader/secmaster/schema.sql")
    if sql_path.exists():
        schema_output_path = docs_path / "secmaster" / "schema.md"
        schema_output_path.parent.mkdir(parents=True, exist_ok=True)
        sql_content = sql_path.read_text()
        parsed = parse_sql_schema(sql_content)
        markdown = generate_markdown(parsed)
        schema_output_path.write_text(markdown)
        logger.info(f"Generated schema documentation: {schema_output_path}")

    # DISCOVER ALL PYTHON MODULES AND SUBMODULES IN src/onesecondtrader
    # ----------------------------------------------------------------------------------

    modules = []
    py_files = []
    submodules = []
    submodule_structure = {}

    for py_file in src_path.glob("*.py"):
        if py_file.name != "__init__.py":
            module_name = py_file.stem
            modules.append(module_name)
            py_files.append(module_name)

    for subdir in src_path.iterdir():
        if subdir.is_dir() and (subdir / "__init__.py").exists():
            submodule_name = subdir.name
            modules.append(submodule_name)
            submodules.append(submodule_name)
            submodule_structure[submodule_name] = discover_package_structure(
                subdir, f"onesecondtrader.{submodule_name}"
            )

    logger.info(f"Found {len(modules)} modules: {', '.join(modules)}")
    if py_files:
        logger.info(f"  - Python files: {', '.join(py_files)}")
    if submodules:
        logger.info(f"  - Submodules: {', '.join(submodules)}")

    # GENERATE INDIVIDUAL MODULE DOCUMENTATION PAGES
    # ----------------------------------------------------------------------------------

    for module in modules:
        title = format_module_title(module)
        module_file = src_path / f"{module}.py"
        submodule_dir = src_path / module

        if submodule_dir.is_dir() and (submodule_dir / "__init__.py").exists():
            structure = submodule_structure[module]
            generate_docs_recursive(
                submodule_dir,
                docs_path / module,
                f"onesecondtrader.{module}",
                structure,
            )
            logger.info(f"Generated docs for submodule {module} (recursive)")

        elif module_file.exists():
            module_content = module_file.read_text()
            has_classes_or_functions = (
                "def " in module_content or "class " in module_content
            )

            if has_classes_or_functions:
                md_content = f"""# {title}

::: onesecondtrader.{module}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
            else:
                indented_content = "\n".join(
                    "    " + line for line in module_content.split("\n")
                )
                md_content = f"""# {title}

::: onesecondtrader.{module}
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

???+ quote "Source code in `{module}.py`"

    ```python linenums="1"
{indented_content}
    ```
"""

            md_file = docs_path / f"{module}.md"
            md_file.write_text(md_content)
            logger.debug(f"Generated {md_file}")
        else:
            logger.warning(
                f"Skipping {module}: neither {module_file} nor {submodule_dir} exists"
            )
            continue

    # GENERATE OVERVIEW PAGE WITH NAVIGATION CARDS
    # ----------------------------------------------------------------------------------

    def get_module_docstring(module_name: str) -> str:
        """Extract the full docstring from a module."""
        if module_name in submodules:
            init_file = src_path / module_name / "__init__.py"
        else:
            init_file = src_path / f"{module_name}.py"

        if not init_file.exists():
            return ""

        content = init_file.read_text()
        lines = content.strip().split("\n")
        if not lines:
            return ""

        first_line = lines[0].strip()
        if first_line.startswith('"""') or first_line.startswith("'''"):
            quote = first_line[:3]
            if first_line.count(quote) >= 2:
                return first_line[3 : first_line.index(quote, 3)].strip()
            docstring_lines = []
            if len(first_line) > 3:
                docstring_lines.append(first_line[3:])
            for line in lines[1:]:
                if quote in line:
                    end_idx = line.index(quote)
                    if end_idx > 0:
                        docstring_lines.append(line[:end_idx])
                    break
                docstring_lines.append(line)
            return "\n".join(docstring_lines).strip()
        return ""

    overview_content = """---
hide:
#  - navigation
#  - toc
---

# Reference

<div class="grid cards" markdown>

"""

    def find_first_file_path(structure: dict, prefix: str) -> str | None:
        """Recursively find the first file path in a package structure."""
        if structure.get("files"):
            first_file = sorted(structure["files"])[0]
            return f"{prefix}/{first_file}.md"
        for subpkg_name in sorted(structure.get("subpackages", {}).keys()):
            subpkg_structure = structure["subpackages"][subpkg_name]
            result = find_first_file_path(subpkg_structure, f"{prefix}/{subpkg_name}")
            if result:
                return result
        return None

    for module in sorted(modules):
        title = format_module_title(module)
        docstring = get_module_docstring(module)

        if module in submodules:
            if module in submodule_structure and submodule_structure[module]:
                structure = submodule_structure[module]
                link_text = f"View `{module}` package API"
                link_target = find_first_file_path(structure, module)

                if not link_target:
                    continue

                if docstring:
                    indented_docstring = "\n    ".join(docstring.split("\n"))
                    overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    {indented_docstring}

    [:material-link-variant: {link_text}]({link_target})
"""
                else:
                    overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    [:material-link-variant: {link_text}]({link_target})
"""
            else:
                continue
        else:
            link_text = f"View `{module}.py` API"

            if docstring:
                indented_docstring = "\n    ".join(docstring.split("\n"))
                overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    {indented_docstring}

    [:material-link-variant: {link_text}]({module}.md)
"""
            else:
                overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    [:material-link-variant: {link_text}]({module}.md)
"""

    overview_content += """
</div>
"""

    overview_file = docs_path / "overview.md"
    overview_file.write_text(overview_content)
    logger.info(f"Generated {overview_file}")

    # UPDATE mkdocs.yml NAVIGATION STRUCTURE
    # ----------------------------------------------------------------------------------

    with open(mkdocs_path) as f:
        config = yaml.unsafe_load(f)

    ref_nav = [{"Overview": "reference/overview.md"}]

    for module in sorted(modules):
        title = format_module_title(module)

        if module in submodules:
            if module in submodule_structure and submodule_structure[module]:
                structure = submodule_structure[module]
                submodule_nav = []

                if module == "secmaster":
                    schema_path = docs_path / "secmaster" / "schema.md"
                    if schema_path.exists():
                        submodule_nav.append(
                            {"Schema": "reference/secmaster/schema.md"}
                        )

                submodule_nav.extend(
                    build_nav_recursive(structure, f"reference/{module}")
                )

                if submodule_nav:
                    ref_nav.append({title: submodule_nav})
                    logger.debug(f"Created hierarchical navigation for {module}")
            else:
                logger.debug(f"Skipping empty submodule {module}")
        else:
            ref_nav.append({title: f"reference/{module}.md"})

    config["nav"] = [
        item
        for item in config["nav"]
        if not (
            isinstance(item, dict) and any("Reference" in key for key in item.keys())
        )
    ]
    config["nav"].append({"Reference": ref_nav})

    with open(mkdocs_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Updated {mkdocs_path}")
    logger.info(f"Success: Generated documentation for {len(modules)} modules")
    logger.info(f"  - {len(py_files)} Python files, {len(submodules)} submodules")


if __name__ == "__main__":
    generate_reference_docs()
