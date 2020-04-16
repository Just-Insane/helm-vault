[![Gitpod Ready-to-Code](https://img.shields.io/badge/Gitpod-Ready--to--Code-blue?logo=gitpod)](https://gitpod.io/#https://github.com/Just-Insane/helm-vault) 

[![License](https://img.shields.io/github/license/Just-Insane/helm-vault.svg)](https://github.com/Just-Insane/helm-vault/blob/master/LICENSE)
[![Current Release](https://img.shields.io/github/release/Just-Insane/helm-vault.svg)](https://github.com/Just-Insane/helm-vault/releases/latest)
[![Production Ready](https://img.shields.io/badge/production-ready-green.svg)](https://github.com/Just-Insane/helm-vault/releases/latest)
[![GitHub issues](https://img.shields.io/github/issues/Just-Insane/helm-vault.svg)](https://github.com/Just-Insane/helm-vault/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/Just-Insane/helm-vault.svg?style=flat-square)](https://github.com/Just-Insane/helm-vault/pulls)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/Just-Insane/helm-vault.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Just-Insane/helm-vault/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/Just-Insane/helm-vault.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/Just-Insane/helm-vault/context:python)
[![Build Status](https://gitlab.com/just.insane/helm-vault/badges/master/pipeline.svg)](https://gitlab.com/just.insane/helm-vault/pipelines)

# Helm-Vault

Helm-Vault stores private data from YAML files in Hashicorp Vault. Helm-Vault should be used if you want to publicize your YAML configuration files, without worrying about leaking secret information.

## Table of Contents

- [Helm-Vault](#helm-vault)
  - [Table of Contents](#table-of-contents)
- [About the Project](#about-the-project)
- [Project Status](#project-status)
- [Getting Started](#getting-started)
  - [Dependencies](#dependencies)
  - [Getting the Source](#getting-the-source)
  - [Running Tests](#running-tests)
    - [Other Tests](#other-tests)
  - [Installation](#installation)
    - [Using Helm plugin manager (> 2.3.x)](#using-helm-plugin-manager--23x)
  - [Usage and Examples](#usage-and-examples)
    - [Basic commands:](#basic-commands)
    - [Usage examples](#usage-examples)
      - [Encrypt](#encrypt)
      - [Decrypt](#decrypt)
      - [View](#view)
      - [Edit](#edit)
      - [Clean](#clean)
    - [Wrapper Examples](#wrapper-examples)
      - [Install](#install)
      - [Template](#template)
      - [Upgrade](#upgrade)
      - [Lint](#lint)
      - [Diff](#diff)
- [Release Process](#release-process)
  - [Versioning](#versioning)
- [How to Get Help](#how-to-get-help)
- [Contributing](#contributing)
- [Further Reading](#further-reading)
- [License](#license)
- [Authors](#authors)
- [Acknowledgments](#acknowledgments)

# About the Project

Helm-Vault supports the following features:

- [X] Encrypt YAML files
- [X] Decrypt YAML files
- [X] View decrypted YAML files
- [X] Edit decrypted YAML files
- [X] Clean up decrypted YAML files
- [X] Helm Wrapper, automatically decrypts and cleans up during helm commands
  - [X] Install
  - [X] Upgrade
  - [X] Template
  - [X] Lint
  - [X] Diff

Helm-Vault was created to provide a better way to manage secrets for Helm, with the ability to take existing public Helm Charts, and with minimal modification, provide a way to have production data that is not stored in a public location.

```
$ helm vault enc values.yaml
Input a value for /mariadb/db/password:
Input a value for /nextcloud/password:
```

**[Back to top](#table-of-contents)**

# Project Status

Build Status:

[![Build Status](https://gitlab.com/just.insane/helm-vault/badges/master/pipeline.svg)](https://gitlab.com/just.insane/helm-vault/pipelines)

Helm-Vault is in a production state. It should work across platforms, and should be able to handle most YAML thrown at it.

**[Back to top](#table-of-contents)**

# Getting Started

To get started with Helm-Vault, follow these steps:

1. Clone the repository to your machine

2. Install the requirements

    `pip3 install -r requirements.txt`

3. Test it out! This will test out encrypting an example YAML file

    `./src/vault.py enc ./tests/test.yaml`

## Dependencies

- [ ] Python 3.7+
- [ ] pip3
- [ ] Working Hashicorp Vault environment
- [ ] Hashicorp Vault token
- [ ] Environment Variables for Vault
  - [ ] VAULT_ADDR: The HTTP Address of Vault
  - [ ] VAULT_TOKEN: The token for accessing Vault

## Getting the Source

This project is [hosted on GitHub](https://github.com/Just-Insane/helm-vault). You can clone this project directly using this command:

```
git clone git@github.com:Justin-Tech/helm-vault.git
```

## Running Tests

Helm-Vault has built-in unit tests using pytest, you can run them with the command below:

```
pip3 install -r ./tests/requirements.txt
python3 -m pytest
```

### Other Tests

Unittesting and integration testing is automatically run on Gitlab per commit.

Additionally, code quality checking is handled by LGTM.com

Both of these checks must pass before PRs will be merged.

## Installation

### Using Helm plugin manager (> 2.3.x)

```
pip3 install git+https://github.com/Just-Insane/helm-vault
helm plugin install https://github.com/Just-Insane/helm-vault
```

## Usage and Examples

```
$ helm vault --help
usage: vault.py [-h] {enc,dec,clean,view,edit} ...

Store secrets from Helm in Vault

Requirements:

Environment Variables:

VAULT_ADDR:     (The HTTP address of Vault, for example, http://localhost:8200)
VAULT_TOKEN:    (The token used to authenticate with Vault)

positional arguments:
  {enc,dec,clean,view,edit}
    enc                 Parse a YAML file and store user entered data in Vault
    dec                 Parse a YAML file and retrieve values from Vault
    clean               Remove decrypted files (in the current directory)
    view                View decrypted YAML file
    edit                Edit decrypted YAML file. DOES NOT CLEAN UP AUTOMATICALLY.

optional arguments:
  -h, --help            show this help message and exit
```

Any YAML file can be transparently "encrypted" as long as it has a deliminator for secret values.

Decrypted files have the suffix ".yaml.dec" by default

### Basic commands:
```
  enc           Encrypt file
  dec           Decrypt file
  view          Print decrypted file
  edit          Edit file (decrypt before, manual cleanup)
  clean         Delete *.yaml.dec files in directory (recursively)
```
Each of these commands have their own help, referenced by `helm vault {enc,dec,clean,view,edit} --help`.

### Usage examples

#### Encrypt

The encrypt operation encrypts a values.yaml file and saves the encrypted values in Vault:

```
$ helm vault enc values.yaml
Input a value for /nextcloud/password: asdf1
Input a value for /mariadb/db/password: asdf2
```

If you don't want to enter the secrets manually on stdin, you can pass a file containing the secrets. Copy `values.yaml` to `values.yaml.dec` and edit the file, replacing "changeme" (the deliminator) with the secret value. Then you can save the secret to vault by running: 

```
$ helm vault enc values.yaml -s values.yaml.dec
```

By default the name of the secret file has to end in `.yaml.dec` so you can add this extension to gitignore to prevent committing a secret to your git repo.

#### Decrypt

The decrypt operation decrypts a values.yaml file and saves the decrypted result in values.yaml.dec:

```
$ helm vault dec values.yaml
```

The values.yaml.dec file:
```
...
nextcloud:
  host: nextcloud.example.com
  username: admin
  password: asdf1
...
mariadb:
parameters
  enabled: true

  db:
    name: nextcloud
    user: nextcloud
    password: asdf2
...
```

#### View

The view operation decrypts values.yaml and prints it to stdout:
```
$ helm vault view values.yaml
```

#### Edit

The edit operation will decrypt the values.yaml file and open it in an editor.

```
$ helm vault edit values.yaml
```

This will read a value from $EDITOR, or be specified with the `-e, --editor` option, or will choose a default of `vi` for Linux/MacOS, and `notepad` for Windows.

Note: This will save a `.dec` file that is not automatically cleaned up.

#### Clean

The operation will delete all decrypted files in a directory:

```
$ helm vault clean
```

### Wrapper Examples

#### Install

The operation wraps the default `helm install` command, automatically decrypting the `-f values.yaml` file and then cleaning up afterwards.

```
$ helm vault install stable/nextcloud --name nextcloud --namespace nextcloud -f values.yaml
```

Specifically, this command will do the following:

1. Run `helm install` with the following options:
  1. `stable/nextcloud` - the chart to install
  1. `--name nextcloud` - the Helm release name will be `nextcloud`
  1. `--namespace nextcloud` - Nextcloud will run in the nextcloud namespace on Kubernetes
  1. `-f values.yaml` - the (encrypted) values file to use

#### Template

The operation wraps the default `helm template` command, automatically decrypting the `-f values.yaml` file and then cleaning up afterwards.

```
$ helm vault template ./nextcloud --name nextcloud --namespace nextcloud -f values.yaml
```

1. Run `helm template` with the following options:
  1. `./nextcloud` - the chart to template
  1. `--name nextcloud` - the Helm release name will be `nextcloud`
  1. `--namespace nextcloud` - Nextcloud will run in the nextcloud namespace on Kubernetes
  1. `-f values.yaml` - the (encrypted) values file to use

#### Upgrade

The operation wraps the default `helm upgrade` command, automatically decrypting the `-f values.yaml` file and then cleaning up afterwards.

```
$ helm vault upgrade nextcloud stable/nextcloud -f values.yaml
```

1. Run `helm upgrade` with the following options:
  1. `nextcloud` - the Helm release name
  1. `stable/nextcloud` - the chart path
  1. `-f values.yaml` - the (encrypted) values file to use

#### Lint

The operation wraps the default `helm lint` command, automatically decrypting the `-f values.yaml` file and then cleaning up afterwards.

```
$ helm vault lint nextcloud -f values.yaml
```

1. Run `helm upgrade` with the following options:
  1. `nextcloud` - the Helm release name
  1. `-f values.yaml` - the (encrypted) values file to use

#### Diff

The operation wraps the `helm diff` command (diff is another Helm plugin), automatically decrypting the `-f values.yaml` file and then cleaning up afterwards.

```
$ helm vault diff upgrade nextcloud stable/nextcloud -f values.yaml
```

1. Run `helm diff upgrade` with the following options:
  1. `nextcloud` - the Helm release name
  1. `stable/nextcloud` - the Helm chart
  1. `-f values.yaml` - the (encrypted) values file to use

**[Back to top](#table-of-contents)**

# Release Process

Releases are made for new features, and bugfixes.

To get a new release, run the following:

```
helm plugin upgrade vault
```

## Versioning

This project uses [Semantic Versioning](http://semver.org/). For a list of available versions, see the [repository tag list](https://github.com/Just-Insane/helm-vault/tags).

**[Back to top](#table-of-contents)**

# How to Get Help

If you need help or have questions, please open an issue with the question label.

# Contributing

We encourage public contributions! Please review [CONTRIBUTING.md](docs/CONTRIBUTING.md) for details on our code of conduct and development process.

**[Back to top](#table-of-contents)**

# Further Reading

[Helm](https://helm.sh/)
[Hashicorp Vault](https://www.vaultproject.io/)

**[Back to top](#table-of-contents)**

# License

Copyright (c) 2019 Justin Gauthier

This project is licensed under GPLv3 - see [LICENSE.md](LICENSE.md) file for details.

**[Back to top](#table-of-contents)**

# Authors

* **[Justin Gauthier](https://github.com/Just-Insane)**

**[Back to top](#table-of-contents)**

# Acknowledgments

The idea for this project comes from [Helm-Secrets](https://github.com/futuresimple/helm-secrets)

Special thanks to the [Python Discord](https://discord.gg/python) server.

**[Back to top](#table-of-contents)**
