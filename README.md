# OneSecondTrader

[![Tests](https://github.com/nilskujath/onesecondtrader/actions/workflows/release.yml/badge.svg)](https://github.com/nilskujath/onesecondtrader/actions/workflows/release.yml)
[![Docs](https://img.shields.io/badge/docs-onesecondtrader.com-blue)](https://www.onesecondtrader.com)
[![PyPI](https://img.shields.io/pypi/v/onesecondtrader)](https://pypi.org/project/onesecondtrader/)
[![License](https://img.shields.io/github/license/nilskujath/onesecondtrader)](https://github.com/nilskujath/onesecondtrader/blob/master/LICENSE)


For documentation, please visit [onesecondtrader.com](https://www.onesecondtrader.com).




## For Developers: Continuous Integration & Delivery (CI/CD) Pipeline

This project's continuous integration & continuous delivery (CI/CD) pipeline consists of two distinct workflows:
 **local pre-commit hooks** that run on `git commit` to ensure code quality,
 and **GitHub Actions** that run on `git push origin master` to automate releases.

In order for the pipeline to work, the following configuration is required:

* version field in `pyproject.toml` must be set to appropriate version
```toml
[tool.poetry]
name = "onesecondtrader"
version = "0.1.0"  # Updated automatically by bump_version.py
```
* `mkdocs.yml` must have `mkdocstrings-python` plugin configured
```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          options:
            docstring_style: google
```

### Local Pre-Commit Workflow

To ensure that only good quality code is commited to the repository, a series of pre-commit hooks are executed before each commit.
 These hooks include code quality checks, testing, security scans, and automated API reference generation.
 This workflow is orchestrated by the `pre-commit` package, which is configured in the `.pre-commit-config.yaml` file.
 If any of these checks fail, the commit is blocked and the developer must fix the issues before retrying.

Prior to usage, the pre-commit hooks must be installed by running:
```bash
poetry run pre-commit install
poetry run pre-commit install --hook-type commit-msg
poetry run pre-commit run --all-files # Optional: Test installation
```

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.
This standardized format enables automated semantic versioning and changelog generation.
The commit messages must have the following format:

```
<type>: <description>

[optional body]

[optional footer(s)]
```

The commit message must start with a type, followed by a colon and a space, and then a description. The type must be one of the following:

- **feat**: New features that add functionality
- **fix**: Bug fixes and patches
- **docs**: Documentation changes only
- **chore**: Maintenance tasks, dependency updates, build changes
- **test**: Adding or modifying tests
- **refactor**: Code changes that neither fix bugs nor add features
- **perf**: Performance improvements
- **ci**: Changes to CI/CD configuration

Examples:

```
feat: added trade-by-trade chart generation 
```

The following diagram illustrates this pre-commit workflow:

```mermaid
---
config:
  themeVariables:
    fontSize: "11px"
---
graph TD
    A([<kbd>git commit</kbd>]) -->|Trigger Pre-commit Workflow on <kbd>commit</kbd>| PrecommitHooks
    
    subgraph PrecommitHooks ["Local Pre-commit Hooks"]
        B["<b>Code Quality Checks</b><br/>• Ruff Check & Format<br/>• MyPy Type Checking<br/>• Tests & Doctests"]
        C["<b>Security Checks</b><br/>• Gitleaks Secret Detection"]
        D["<b>File Validation</b><br/>• YAML/TOML/JSON Check<br/>• End-of-file Fixer<br/>• Large Files Check<br/>• Merge Conflict Check<br/>• Debug Statements Check"]
        E["<b>Generate API Documentation</b> via <kbd>scripts/generate_api_docs.py</kbd><br/>• Auto-generate docs<br/>• Stage changes"]
    end
    B --> C --> D --> E

    F([Write Commit Message])
    PrecommitHooks -->|Pass| F
    PrecommitHooks -.->|Fail| H

    subgraph CommitMessageHook ["Commit Message Hook"]
        G{Commit Message Valid?}
    end
        G -.->|No| H[Commit Blocked]
        G -->|Yes| I[Commit Successful]

    F --> CommitMessageHook

    H -.->|Rework & Restage<br/>| K
    
    K(["<kbd>git commit --amend</kbd>"])

    K -.-> PrecommitHooks

    L(["<kbd>git pull --rebase origin master</kbd>"])

    L -.->|Rebase & Resolve Conflicts| M
    
    M([<kbd>git add <...></kbd>])
    
    M -.-> A

    I -.~.-> J([<kbd>git push</kbd>])
```


### GitHub Actions Workflow

Once a commit is pushed to the remote `master` branch, the GitHub Actions workflow `.github/workflows/release.yml` is triggered.
Note that the GitHub Actions workflow might push commits to the remote repository.
 This means your local branch will be behind the remote branch.

In order for this workflow to run properly, two secrets need to be configured (`Settings > Secrets and variables > Actions`):

- `GH_PAT`: Personal Access Token with enhanced permissions (see PAT Setup below)
- `PYPI_API_TOKEN`: Generate from PyPI account settings

The default `GITHUB_TOKEN` has limited permissions and cannot trigger subsequent workflow runs or push to protected branches.
 The PAT provides the necessary permissions for the automated release process. 
 The PAT is created as follows:

1. Go to GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)
2. Click "Generate new token (classic)"
3. Set expiration and select these scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
4. Copy the token and add it as `GH_PAT` secret in repository settings

Note that GitHub Actions bot must have write permissions to the repository.

The following diagram illustrates this GitHub Actions workflow:

```mermaid
---
config:
  themeVariables:
    fontSize: "11px"
---
graph TD
    
    A0(<kdb>git commit</kbd>)

    A1(<kdb>git commit --amend</kdb>)

    A(<kbd>git push origin master</kbd>) -->|Trigger GitHub Actions Workflow on <kbd>push</kbd>| GitHubActions

    A2(<kbd>git push origin master --force</kbd>) -->|Trigger GitHub Actions Workflow on <kbd>push</kbd>| GitHubActions

    A0 -.->|Trigger Pre-commit Workflow & Commit| A
    A1 -.->|Trigger Pre-commit Workflow & Commit| A2
    
    subgraph GitHubActions ["GitHub Actions Environment Setup"]
        B["<b>Checkout Repository</b><br/>Retrieve the full repository history on the latest Ubuntu runner"]
        C["<b>Setup Python Environment</b><br/>Configure the required Python version and install Poetry"]
        D["<b>Install Dependencies</b><br/>Install all project dependencies, including development ones"]
        B --> C --> D
    end

    GitHubActions -.->|Failure<br/>Rework & Restage| A3
    A3(<kdb>git commit --amend</kdb>)

    GitHubActions -->|Environment Setup Complete| QualityChecks
    
    subgraph QualityChecks ["CI Quality Validation"]
        F["<b>Ruff Linting</b><br/>Validate code style and enforce formatting rules"]
        G["<b>MyPy Type Checking</b><br/>Static type analysis"]
        H["<b>Test Suite</b><br/>Run all automated tests"]
        F --> G --> H
    end
   
    QualityChecks -.->|Failure<br/>Rework & Restage| A3

    QualityChecks -->|CI Quality Checks Passed| GitConfig
    
    subgraph GitConfig ["Git Configuration"]
        J["<b>Configure Git Identity</b><br/>Set the automated commit author for CI operations"]
        K["<b>Setup Authentication</b><br/>Enable secure access to the repository with release permissions (requires <kbd>GH_PAT</kbd>)"]
        J --> K
    end

    GitConfig -->|Git Configured| VersionAnalysis
    
    subgraph VersionAnalysis ["Semantic Version Analysis"]
        N["<b>Execute bump_version.py</b><br/>Analyze commits since last tag to decide on version bump and bump level"]
        P{Version Bump Required?}
        N --> P
    end
    
    VersionAnalysis -->|No Version Change<br/>Skip Release Process| DocDeployment
    VersionAnalysis -->|Version Bump Required| ReleaseProcess
    
    
    subgraph ReleaseProcess ["Release & Publishing"]
        R["<b>Update Version & Changelog</b><br/>Write new version and regenerate release notes."]
        S["<b>Commit & Push</b><br/>Commit updated files and push to the default branch."]
        T["<b>Publish to PyPI</b><br/>Build and upload distributions in one step."]
        U["<b>Create GitHub Release</b><br/>Publish tag and attach changelog."]
        R --> S --> T --> U
    end

    
    ReleaseProcess -->|Release Complete| DocDeployment 
    
    subgraph DocDeployment ["Documentation Deployment"]
        X["<b>Generate API Documentation</b><br/>Automatically build API docs and update navigation"]
        Y["<b>Install Package for Docs</b><br/>Prepare project for import-based documentation"]
        Z["<b>Deploy to GitHub Pages</b><br/>Publish updated documentation site"]
        X --> Y --> Z
    end
```
