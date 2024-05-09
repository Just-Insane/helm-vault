# CHANGELOG.md

## 0.3.1 (2024-05-09)

Fix:

- Update GitPython [fixes #55]
- Update to CodeQL from LGTM.com
- Move from `vault` Docker container to `hashicorp/vault` in automated tests

## 0.3.0 (2021-03-17)

Features:

- Adds an option to set an environment for secrets, using the -e/--environment flag
  - Moves the editor selection from -e to -ed

Fix:

- Moved from gitlab-ci to Github Actions for CI
