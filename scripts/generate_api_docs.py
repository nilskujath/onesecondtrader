#!/usr/bin/env python3
import logging
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "docs"))
from hooks import parse_sql_schema, generate_markdown

# SETUP LOGGER
# --------------------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# API REFERENCE DOCUMENTATION GENERATION
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


def generate_api_docs():
    """Generate API reference documentation from docstrings via mkdocstrings package.

    Automatically discovers Python modules and submodules in src/onesecondtrader and generates
    corresponding markdown documentation files. Handles both:
    - Top-level .py files (like monitoring.py)
    - Submodule structure (like domain/ with __init__.py)

    Modules with substantial content use mkdocstrings for automatic API documentation, while
    simple modules display their source code directly. This is done in the following steps:

        1. Clean and recreate docs/api-reference directory
        2. Discover all Python modules and submodules (excluding __init__.py)
        3. Generate individual module documentation pages
        4. Create overview page with navigation cards
        5. Update mkdocs.yml navigation structure with hierarchical organization

    Submodules are always processed with mkdocstrings since they typically contain substantial
    content. Regular .py files are analyzed for content complexity.

    Output:
        - Individual .md files for each module/submodule in docs/api-reference/
        - Overview page at docs/api-reference/overview.md with correct file type indicators
        - Updated navigation in mkdocs.yml with proper module/submodule organization

    Raises:
        FileNotFoundError: If not run from project root directory.

    Note:
        This script must be run from the project root directory.
    """
    logger.info("Starting to generate API documentation...")

    # VALIDATE THAT WE'RE IN THE PROJECT ROOT DIRECTORY
    # ----------------------------------------------------------------------------------

    src_path = Path("src/onesecondtrader")
    mkdocs_path = Path("mkdocs.yml")

    if not src_path.exists() or not mkdocs_path.exists():
        logger.error("Script must be run from the project root directory.")
        raise FileNotFoundError("Script must be run from the project root directory. ")

    # CLEAN AND RECREATE API REFERENCE DOCS DIRECTORY
    # ----------------------------------------------------------------------------------

    docs_path = Path("docs/api-reference")
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

    # Find top-level .py files (excluding __init__.py)
    for py_file in src_path.glob("*.py"):
        if py_file.name != "__init__.py":
            module_name = py_file.stem
            modules.append(module_name)
            py_files.append(module_name)

    # Find submodules (directories with __init__.py)
    for subdir in src_path.iterdir():
        if subdir.is_dir() and (subdir / "__init__.py").exists():
            submodule_name = subdir.name
            modules.append(submodule_name)
            submodules.append(submodule_name)

    logger.info(f"Found {len(modules)} modules: {', '.join(modules)}")
    if py_files:
        logger.info(f"  - Python files: {', '.join(py_files)}")
    if submodules:
        logger.info(f"  - Submodules: {', '.join(submodules)}")

    # GENERATE INDIVIDUAL MODULE DOCUMENTATION PAGES
    # ----------------------------------------------------------------------------------

    submodule_structure = {}  # Track submodule structure for navigation

    for module in modules:
        title = format_module_title(module)

        # Check if this is a submodule (directory) or a regular module (.py file)
        module_file = src_path / f"{module}.py"
        submodule_dir = src_path / module

        if submodule_dir.is_dir() and (submodule_dir / "__init__.py").exists():
            # This is a submodule - create subfolder structure
            submodule_docs_dir = docs_path / module
            submodule_docs_dir.mkdir(exist_ok=True)

            # Find all Python files in the submodule (excluding __init__.py)
            submodule_files = []
            for py_file in submodule_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    submodule_files.append(py_file.stem)

            # Find nested submodules (directories with __init__.py)
            nested_submodules = {}
            for nested_dir in submodule_dir.iterdir():
                if nested_dir.is_dir() and (nested_dir / "__init__.py").exists():
                    nested_name = nested_dir.name
                    nested_files = []
                    for py_file in nested_dir.glob("*.py"):
                        if py_file.name != "__init__.py":
                            nested_files.append(py_file.stem)
                    if nested_files:
                        nested_submodules[nested_name] = nested_files

            logger.info(
                f"Processing submodule {module} with files: {', '.join(submodule_files)}, "
                f"nested: {list(nested_submodules.keys())}"
            )

            # Store submodule structure for navigation (include nested)
            submodule_structure[module] = {
                "files": submodule_files,
                "nested": nested_submodules,
            }

            # Generate documentation for each file in the submodule
            for subfile in submodule_files:
                subfile_title = format_module_title(subfile)
                subfile_path = submodule_dir / f"{subfile}.py"
                subfile_content = subfile_path.read_text()

                has_classes_or_functions = (
                    "def " in subfile_content or "class " in subfile_content
                )

                if has_classes_or_functions:
                    md_content = f"""# {subfile_title}

::: onesecondtrader.{module}.{subfile}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
                else:
                    indented_content = "\n".join(
                        "    " + line for line in subfile_content.split("\n")
                    )

                    md_content = f"""# {subfile_title}

::: onesecondtrader.{module}.{subfile}
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

???+ quote "Source code in `{subfile}.py`"

    ```python linenums="1"
{indented_content}
    ```
"""

                subfile_md = submodule_docs_dir / f"{subfile}.md"
                subfile_md.write_text(md_content)
                logger.debug(f"Generated {subfile_md}")

            # Generate documentation for nested submodules
            for nested_name, nested_files in nested_submodules.items():
                nested_docs_dir = submodule_docs_dir / nested_name
                nested_docs_dir.mkdir(exist_ok=True)

                for nested_file in nested_files:
                    nested_file_title = format_module_title(nested_file)
                    nested_file_path = submodule_dir / nested_name / f"{nested_file}.py"
                    nested_file_content = nested_file_path.read_text()

                    has_classes_or_functions = (
                        "def " in nested_file_content or "class " in nested_file_content
                    )

                    if has_classes_or_functions:
                        md_content = f"""# {nested_file_title}

::: onesecondtrader.{module}.{nested_name}.{nested_file}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
                    else:
                        indented_content = "\n".join(
                            "    " + line for line in nested_file_content.split("\n")
                        )

                        md_content = f"""# {nested_file_title}

::: onesecondtrader.{module}.{nested_name}.{nested_file}
    options:
      show_root_heading: False
      show_source: false
      heading_level: 2
      show_root_toc_entry: False

???+ quote "Source code in `{nested_file}.py`"

    ```python linenums="1"
{indented_content}
    ```
"""

                    nested_file_md = nested_docs_dir / f"{nested_file}.md"
                    nested_file_md.write_text(md_content)
                    logger.debug(f"Generated {nested_file_md}")

        elif module_file.exists():
            # This is a regular .py file - check if it has substantial content
            module_content = module_file.read_text()

            # Simple check for classes or functions
            has_classes_or_functions = (
                "def " in module_content or "class " in module_content
            )

            if has_classes_or_functions:
                # Use mkdocstrings for modules with classes/functions
                md_content = f"""# {title}

::: onesecondtrader.{module}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
            else:
                # Indent the module content for the admonition
                indented_content = "\n".join(
                    "    " + line for line in module_content.split("\n")
                )

                # Manual source code display for simple modules
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
            # Skip if neither file nor directory exists
            logger.warning(
                f"Skipping {module}: neither {module_file} nor {submodule_dir} exists"
            )
            continue

    # GENERATE OVERVIEW PAGE WITH NAVIGATION CARDS
    # ----------------------------------------------------------------------------------

    overview_content = """---
hide:
#  - navigation
#  - toc
---

# :material-text-box-search-outline: **API** Reference

<div class="grid cards" markdown>

"""

    # Add all modules in alphabetical order regardless of type
    for module in sorted(modules):
        title = format_module_title(module)

        if module in submodules:
            # This is a submodule
            if module in submodule_structure and submodule_structure[module]:
                structure = submodule_structure[module]
                link_text = f"View `{module}` package API"

                # Find the first available file to link to
                files = structure.get("files", [])
                nested = structure.get("nested", {})

                if files:
                    first_file = sorted(files)[0]
                    link_target = f"{module}/{first_file}.md"
                elif nested:
                    first_nested = sorted(nested.keys())[0]
                    first_nested_file = sorted(nested[first_nested])[0]
                    link_target = f"{module}/{first_nested}/{first_nested_file}.md"
                else:
                    continue  # Skip empty modules

                overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    [:material-link-variant: {link_text}]({link_target})
"""
            else:
                # Skip submodules without discoverable files
                continue
        else:
            # This is a regular Python file
            link_text = f"View `{module}.py` API"

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

    # Build API Reference navigation with hierarchical structure
    api_nav = [{"Overview": "api-reference/overview.md"}]

    # Sort all modules alphabetically regardless of type (Python files or submodules)
    sorted_modules = sorted(modules)

    # Add modules in alphabetical order
    for module in sorted_modules:
        title = format_module_title(module)

        if module in submodules:
            # This is a submodule - create hierarchical navigation
            if module in submodule_structure and submodule_structure[module]:
                structure = submodule_structure[module]
                submodule_nav = []

                # Special case: add schema.md for secmaster if it exists
                if module == "secmaster":
                    schema_path = docs_path / "secmaster" / "schema.md"
                    if schema_path.exists():
                        submodule_nav.append(
                            {"Schema": "api-reference/secmaster/schema.md"}
                        )

                # Add direct files
                for subfile in sorted(structure.get("files", [])):
                    subfile_title = format_module_title(subfile)
                    submodule_nav.append(
                        {subfile_title: f"api-reference/{module}/{subfile}.md"}
                    )

                # Add nested submodules
                for nested_name in sorted(structure.get("nested", {}).keys()):
                    nested_files = structure["nested"][nested_name]
                    nested_title = format_module_title(nested_name)
                    nested_nav = []
                    for nested_file in sorted(nested_files):
                        nested_file_title = format_module_title(nested_file)
                        nested_nav.append(
                            {
                                nested_file_title: f"api-reference/{module}/{nested_name}/{nested_file}.md"
                            }
                        )
                    submodule_nav.append({nested_title: nested_nav})

                if submodule_nav:
                    api_nav.append({title: submodule_nav})
                    logger.debug(
                        f"Created hierarchical navigation for {module}: {len(submodule_nav)} items"
                    )
            else:
                # Fallback for submodules without discoverable files - skip
                logger.debug(f"Skipping empty submodule {module}")
        else:
            # This is a regular Python file
            api_nav.append({title: f"api-reference/{module}.md"})

    # Update navigation - remove existing API Reference and add new one
    config["nav"] = [
        item
        for item in config["nav"]
        if not (isinstance(item, dict) and "API Reference" in item)
    ]
    config["nav"].append({"API Reference": api_nav})

    # Write updated mkdocs.yml
    with open(mkdocs_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Updated {mkdocs_path}")
    logger.info(
        f"Success: Generated documentation for {len(modules)} modules (alphabetically ordered)"
    )
    logger.info(f"  - {len(py_files)} Python files, {len(submodules)} submodules")

    # Log the hierarchical structure created
    for module, structure in submodule_structure.items():
        files = structure.get("files", [])
        nested = structure.get("nested", {})
        nested_count = sum(len(v) for v in nested.values())
        logger.info(
            f"  - Submodule {module}: {len(files)} files, {len(nested)} nested structure ({nested_count} files)"
        )


if __name__ == "__main__":
    generate_api_docs()
