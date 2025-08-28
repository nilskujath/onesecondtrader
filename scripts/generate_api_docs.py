#!/usr/bin/env python3
import logging
import shutil
from pathlib import Path

import yaml

# SETUP LOGGER
# --------------------------------------------------------------------------------------


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# API REFERENCE DOCUMENTATION GENERATION
# --------------------------------------------------------------------------------------


def generate_api_docs():
    """Generate API reference documentation from docstrings via mkdocstrings package.

    Automatically discovers Python modules and submodules in src/onesecondtrader and generates
    corresponding markdown documentation files. Handles both:
    - Top-level .py files (like monitoring.py)
    - Submodule packages (like domain/ with __init__.py)

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
        title = module.replace("_", " ").title()

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

            logger.info(
                f"Processing submodule {module} with files: {', '.join(submodule_files)}"
            )

            # Store submodule structure for navigation
            submodule_structure[module] = submodule_files

            # Generate documentation for each file in the submodule
            for subfile in submodule_files:
                subfile_title = subfile.replace("_", " ").title()
                subfile_path = submodule_dir / f"{subfile}.py"
                subfile_content = subfile_path.read_text()

                # Check if this subfile has substantial content
                has_classes_or_functions = (
                    "def " in subfile_content or "class " in subfile_content
                )

                if has_classes_or_functions:
                    # Use mkdocstrings for files with classes/functions
                    md_content = f"""# {subfile_title}

::: onesecondtrader.{module}.{subfile}
    options:
      show_root_heading: False
      show_source: true
      heading_level: 2
      show_root_toc_entry: False
"""
                else:
                    # Manual source code display for simple files
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

??? quote "Source code in `{subfile}.py`"

    ```python linenums="1"
{indented_content}
    ```
"""

                subfile_md = submodule_docs_dir / f"{subfile}.md"
                subfile_md.write_text(md_content)
                logger.debug(f"Generated {subfile_md}")

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

??? quote "Source code in `{module}.py`"

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
        title = module.replace("_", " ").title()

        if module in submodules:
            # This is a submodule
            if module in submodule_structure and submodule_structure[module]:
                # Show submodule with its files
                files_list = ", ".join(
                    [f"`{f}.py`" for f in sorted(submodule_structure[module])]
                )
                link_text = f"View `{module}/` package API"

                # Point to the alphabetically first submodule file
                first_submodule = sorted(submodule_structure[module])[0]
                link_target = f"{module}/{first_submodule}.md"

                overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    Contains: {files_list}

    ---

    [:material-link-variant: {link_text}]({link_target})
"""
            else:
                # Fallback for submodules without discoverable files
                link_text = f"View `{module}/` package API"
                overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    [:material-link-variant: {link_text}]({module}.md)
"""
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
        title = module.replace("_", " ").title()

        if module in submodules:
            # This is a submodule - create hierarchical navigation
            if module in submodule_structure and submodule_structure[module]:
                # Create hierarchical navigation for submodules with files
                submodule_nav = []
                for subfile in sorted(submodule_structure[module]):
                    subfile_title = subfile.replace("_", " ").title()
                    submodule_nav.append(
                        {subfile_title: f"api-reference/{module}/{subfile}.md"}
                    )

                api_nav.append({title: submodule_nav})
                logger.debug(
                    f"Created hierarchical navigation for {module}: {len(submodule_nav)} files"
                )
            else:
                # Fallback for submodules without discoverable files
                api_nav.append({title: f"api-reference/{module}.md"})
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
    for module, files in submodule_structure.items():
        logger.info(f"  - Submodule {module}: {len(files)} files ({', '.join(files)})")


if __name__ == "__main__":
    generate_api_docs()
