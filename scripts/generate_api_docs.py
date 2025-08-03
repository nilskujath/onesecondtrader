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


########################################################################################
# API REFERENCE DOCUMENTATION GENERATION
########################################################################################


def generate_api_docs():
    """Generate comprehensive API documentation for the onesecondtrader package.

    Automatically discovers Python modules in src/onesecondtrader and generates
    corresponding markdown documentation files. Modules with substantial content
    (classes/functions) use mkdocstrings for automatic API documentation, while
    simple modules display their source code directly.

    Process:
        1. Clean and recreate docs/api-reference directory
        2. Discover all Python modules (excluding __init__.py)
        3. Generate individual module documentation pages
        4. Create overview page with navigation cards
        5. Update mkdocs.yml navigation structure

    Output:
        - Individual .md files for each module in docs/api-reference/
        - Overview page at docs/api-reference/overview.md
        - Updated navigation in mkdocs.yml

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

    # DISCOVER ALL PYTHON MODULES IN src/onesecondtrader (EXCLUDING __init__.py)
    # ----------------------------------------------------------------------------------

    modules = []
    for py_file in src_path.glob("*.py"):
        if py_file.name != "__init__.py":
            module_name = py_file.stem
            modules.append(module_name)

    logger.info(f"Found {len(modules)} modules: {', '.join(modules)}")

    # GENERATE INDIVIDUAL MODULE DOCUMENTATION PAGES
    # ----------------------------------------------------------------------------------

    for module in modules:
        title = module.replace("_", " ").title()

        # Check if module has substantial content (classes/functions)
        module_file = src_path / f"{module}.py"
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

    for module in sorted(modules):
        title = module.replace("_", " ").title()

        overview_content += f"""
-   __{title}__&nbsp;&nbsp;

    ---

    [:material-link-variant: View `{module}.py` API]({module}.md)
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

    # Build API Reference navigation
    api_nav = [{"Overview": "api-reference/overview.md"}]

    for module in sorted(modules):
        title = module.replace("_", " ").title()
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
    logger.info(f"Success: Generated documentation for {len(modules)} modules")


if __name__ == "__main__":
    generate_api_docs()
