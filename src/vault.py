#!/usr/bin/env python3

import re
import ruamel.yaml
import hvac
import os
import argparse
RawTextHelpFormatter = argparse.RawTextHelpFormatter
import glob
import sys
import git
import platform
import subprocess
check_call = subprocess.check_call


if sys.version_info[:2] < (3, 7):
    raise Exception("Python 3.7 or a more recent version is required.")

def parse_args(args):
    # Help text
    parser = argparse.ArgumentParser(description=
    """Store secrets from Helm in Vault
    \n
    Requirements:
    \n
    Environment Variables:
    \n
    VAULT_ADDR:         (The HTTP address of Vault, for example, http://localhost:8200)
    VAULT_TOKEN:        (The token used to authenticate with Vault)
    VAULT_NAMESPACE:    (The Vault Namespace to use (Vault enterprise only))
    """, formatter_class=RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Encrypt help
    encrypt = subparsers.add_parser("enc", help="Parse a YAML file and store user entered data in Vault")
    encrypt.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    encrypt.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    encrypt.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    encrypt.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault) Default: \"secret/helm\"")
    encrypt.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    encrypt.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    encrypt.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v2\"")
    encrypt.add_argument("-s", "--secret-file", type=str, help="File containing the secret for input. Must end in .yaml.dec")
    encrypt.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")
    encrypt.add_argument("-e", "--environment", type=str, help="Allows for secrets to be encoded on a per environment basis")

    # Decrypt help
    decrypt = subparsers.add_parser("dec", help="Parse a YAML file and retrieve values from Vault")
    decrypt.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    decrypt.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    decrypt.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    decrypt.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    decrypt.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    decrypt.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    decrypt.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    decrypt.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")
    decrypt.add_argument("-e", "--environment", type=str, help="Allows for secrets to be decoded on a per environment basis")

    # Clean help
    clean = subparsers.add_parser("clean", help="Remove decrypted files (in the current directory)")
    clean.add_argument("-f", "--file", type=str, help="The specific YAML file to be deleted, without .dec", dest="yaml_file")
    clean.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")
    clean.add_argument("-e", "--environment", type=str, help="Decoded environment to clean")

    # View Help
    view = subparsers.add_parser("view", help="View decrypted YAML file")
    view.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    view.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    view.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    view.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    view.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    view.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    view.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    view.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Edit Help
    edit = subparsers.add_parser("edit", help="Edit decrypted YAML file. DOES NOT CLEAN UP AUTOMATICALLY.")
    edit.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    edit.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    edit.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    edit.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    edit.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    edit.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    edit.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    edit.add_argument("-ed", "--editor", help="Editor name. Default: (Linux/MacOS) \"vi\" (Windows) \"notepad\"", const=True, nargs="?")
    edit.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Install Help
    install = subparsers.add_parser("install", help="Wrapper that decrypts YAML files before running helm install")
    install.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    install.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    install.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    install.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    install.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    install.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    install.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    install.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")
    install.add_argument("-e", "--environment", type=str, help="Environment whose secrets to use")

    # Template Help
    template = subparsers.add_parser("template", help="Wrapper that decrypts YAML files before running helm install")
    template.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    template.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    template.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    template.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    template.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    template.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    template.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    template.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Upgrade Help
    upgrade = subparsers.add_parser("upgrade", help="Wrapper that decrypts YAML files before running helm install")
    upgrade.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    upgrade.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    upgrade.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    upgrade.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    upgrade.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    upgrade.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    upgrade.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    upgrade.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Lint Help
    lint = subparsers.add_parser("lint", help="Wrapper that decrypts YAML files before running helm install")
    lint.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    lint.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    lint.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    lint.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    lint.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    lint.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    lint.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    lint.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Diff Help
    diff = subparsers.add_parser("diff", help="Wrapper that decrypts YAML files before running helm diff")
    diff.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    diff.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    diff.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    diff.add_argument("-mp", "--mountpoint", type=str, help="The Vault Mount Point Default: \"secret/data\"")
    diff.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    diff.add_argument("-vtp", "--vaulttemplatepath", type=str,
                         help="A preifx to use when retrieving values based on their vaulttemplate value. Default: \"\"")
    diff.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    diff.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    return parser

class Git:
    def __init__(self, cwd):
        self.cwd = cwd

    def get_git_root(self):
        try:
            self.git_repo = git.Repo(self.cwd, search_parent_directories=True)
            self.git_root = self.git_repo.git.rev_parse("--show-toplevel")
            return self.git_root
        except Exception as ex:
            print(f"There was an error finding the root git repository, please specify a path within the yaml file. For more information, see Vault Path Templating: https://github.com/Just-Insane/helm-vault#vault-path-templating")

class Envs:
    def __init__(self, args):
        self.args = args
        self.vault_addr = os.environ["VAULT_ADDR"]
        self.vault_mount_point = self.get_env("VAULT_MOUNT_POINT", "mountpoint", "secret")
        self.vault_path = self.get_env("VAULT_PATH", "vaultpath", "secret/helm")
        self.vault_base_path = self.get_env("VAULT_TEMPLATE_PATH", "vaulttemplatepath", "")
        self.secret_delim = self.get_env("SECRET_DELIM", "deliminator", "changeme")
        self.secret_template = self.get_env("SECRET_TEMPLATE", "vaulttemplate", "VAULT:")
        self.kvversion = self.get_env("KVVERSION", "kvversion", "v1")
        self.environment = self.get_env("NONE", "environment", "")

        if platform.system() != "Windows":
            editor_default = "vi"
        else:
            editor_default = "notepad"

        self.editor = self.get_env("EDITOR", "edit", editor_default)

    def get_env(self, environment_var_name, arg_name, default_value):
        value = None

        if environment_var_name in os.environ:
            value=os.environ[environment_var_name]
            source="ENVIRONMENT"

        if hasattr(self.args, arg_name):
            v = getattr(self.args, arg_name)
            if v:
                value = v
                source = "ARG"

        if value is None and default_value is not None:
            value = default_value
            source = "DEFAULT"

        if self.args.verbose is True:
            print(f"The {source} {arg_name} is: {value}")

        return value

class Vault:
    def __init__(self, args, envs):
        self.args = args
        self.envs = envs
        self.folder = Git(os.getcwd())
        self.folder = self.folder.get_git_root()
        self.folder = os.path.basename(self.folder)
        self.kvversion = envs.kvversion

        # Setup Vault client (hvac)
        try:
            self.client = hvac.Client(url=self.envs.vault_addr, namespace=os.environ.get("VAULT_NAMESPACE"), token=os.environ["VAULT_TOKEN"])
        except KeyError:
            print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
        except Exception as ex:
            print(f"ERROR: {ex}")

    def process_mount_point_and_path(self, full_path, path, key):
        print(full_path)
        if full_path is not None:
          # vault_base_path overrides all other paths and uses full_path to finish the path
          if self.envs.vault_base_path != "":
              # If it starts with /, treat it as the mount_point + path
              if self.envs.vault_base_path.startswith('/'):
                  mount_point = self.envs.vault_base_path.split('/')[1]
                  _path = f"{'/'.join(self.envs.vault_base_path.split('/')[2:])}/{full_path}"
              else:
                  mount_point =  self.envs.vault_mount_point
                  _path = f"{self.envs.vault_base_path}/{full_path}"
          else:
            _path = full_path
            if _path.startswith('/'):
                mount_point = _path.split('/')[1]
                _path = '/'.join(_path.split('/')[2:])
            else:
                mount_point =  self.envs.vault_path.split('/')[0]
        else:
            print("No full_path")
            mount_point = self.envs.vault_mount_point
            _path = f"{self.envs.vault_path}/{self.folder}{path}/{key}"

        return mount_point, _path

    def vault_write(self, value, path, key, full_path=None):
        # Use path from template if presents
        mount_point, _path = self.process_mount_point_and_path(full_path, path, key)

        # Write to vault, using the correct Vault KV version
        try:
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
                print(f"Attempting to write to url: {self.envs.vault_addr}/v1/{mount_point}/data{_path}")

            if self.kvversion == "v1":
                self.client.write(_path, value=value, mount_point = mount_point)
            elif self.kvversion == "v2":
                self.client.secrets.kv.v2.create_or_update_secret(
                    path=_path,
                    secret=dict(value=value),
                    mount_point = mount_point,
                )
            else:
                print("Wrong KV Version specified, either v1 or v2")
        except AttributeError:
            print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
        except Exception as ex:
            print(f"Error: {ex}")

        if self.args.verbose is True:
            print(f"Wrote {value} to: {_path}")

    def vault_read(self, value, path, key, full_path=None):
        mount_point, _path = self.process_mount_point_and_path(full_path, path, key)

        # Read from Vault, using the correct Vault KV version
        try:
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
                print(f"Attempting to read from url: {self.envs.vault_addr}/v1/{mount_point}/data/{_path}")
            if self.kvversion in ['v1', 'v2']:
                if self.kvversion == "v1":
                    value = self.client.read(_path)
                    value = value.get("data", {}).get("value")
                else:
                    value = self.client.secrets.kv.v2.read_secret_version(path=_path,mount_point=mount_point)
                    value = value.get("data", {}).get("data", {}).get("value")
                return value
            else:
                print("Wrong KV Version specified, either v1 or v2")
        except AttributeError as ex:
            print(f"Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables. {ex}")
        except Exception as ex:
            print(f"Error: {ex}")

def load_yaml(yaml_file):
    # Load the YAML file
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    with open(yaml_file) as filepath:
        data = yaml.load(filepath)
        return data

def cleanup(args, envs):
    # Cleanup decrypted files
    yaml_file = args.yaml_file
    decode_file = '.'.join(filter(None, [yaml_file, envs.environment, 'dec']))
    try:
        os.remove(decode_file)
        if args.verbose is True:
            print(f"Deleted {decode_file}")
    except AttributeError:
        for fl in glob.glob("*.dec"):
            os.remove(fl)
            if args.verbose is True:
                print(f"Deleted {fl}")
    except Exception as ex:
        print(f"Error: {ex}")

# Get value from a nested hash structure given a path of key names
# For example:
# secret_data['mysql']['password'] = "secret"
# value_from_path(secret_data, "/mysql/password") => returns "secret"
def value_from_path(secret_data, path):
    val = secret_data
    for key in path.split('/'):
        if not key:
            continue
        if key in val.keys():
            val = val[key]
        else:
            raise Exception(f"Missing secret value. Key {key} does not exist when retrieving value from path {path}")
    return val

def dict_walker(pattern, data, args, envs, secret_data, path=None):
    # Walk through the loaded dicts looking for the values we want
    environment = f"/{envs.environment}" if envs.environment else ""

    path = path if path is not None else environment
    action = args.action
    if isinstance(data, dict):
        for key, value in data.items():
            if value == pattern or str(value).startswith(envs.secret_template):
                if value.startswith(envs.secret_template):
                    _full_path = value[len(envs.secret_template):].replace("{environment}", environment)
                else:
                    _full_path = None
                if action == "enc":
                    path_sans_env = path.replace(environment, '')
                    if secret_data:
                        data[key] = value_from_path(secret_data, f"{path_sans_env}/{key}")
                    else:
                        path_to_property_syntax = path_sans_env.replace("/", ".")[1:]
                        data[key] = input(f"Input a value for {path_to_property_syntax}.{key}: ")
                    vault = Vault(args, envs)
                    vault.vault_write(data[key], path, key, _full_path)
                elif (action == "dec") or (action == "view") or (action == "edit") or (action == "install") or (action == "template") or (action == "upgrade") or (action == "lint") or (action == "diff"):
                    vault = Vault(args, envs)
                    vault = vault.vault_read(value, path, key, _full_path)
                    value = vault
                    data[key] = value
            for res in dict_walker(pattern, value, args, envs, secret_data, path=f"{path}/{key}"):
                yield res
    elif isinstance(data, list):
        for item in data:
            for res in dict_walker(pattern, item, args, envs, secret_data, path=f"{path}"):
                yield res


def load_secret(args):
    if args.secret_file:
        if not re.search(r'\.yaml\.dec$', args.secret_file):
            raise Exception(f"ERROR: Secret file name must end with \".yaml.dec\". {args.secret_file} was given instead.")
        return load_yaml(args.secret_file)

def main(argv=None):

    # Parse arguments from argparse
    # This is outside of the parse_arg function because of issues returning multiple named values from a function
    parsed = parse_args(argv)
    args, leftovers = parsed.parse_known_args(argv)

    yaml_file = args.yaml_file
    data = load_yaml(yaml_file)
    action = args.action

    envs = Envs(args)

    if action == "clean":
        cleanup(args, envs)

    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    secret_data = load_secret(args) if args.action == 'enc' else None

    for path, key, value in dict_walker(envs.secret_delim, data, args, envs, secret_data):
        print("Done")
    
    decode_file = '.'.join(filter(None, [yaml_file, envs.environment, 'dec']))

    if action == "dec":
        yaml.dump(data, open(decode_file, "w"))
        print("Done Decrypting")
    elif action == "view":
        yaml.dump(data, sys.stdout)
    elif action == "edit":
        yaml.dump(data, open(decode_file, "w"))
        os.system(envs.editor + ' ' + f"{decode_file}")
    # These Helm commands are only different due to passed variables
    elif (action == "install") or (action == "template") or (action == "upgrade") or (action == "lint") or (action == "diff"):
        yaml.dump(data, open(decode_file, "w"))
        leftovers = ' '.join(leftovers)

        try:
            cmd = f"helm {args.action} {leftovers} -f {decode_file}"
            if args.verbose is True:
                print(f"About to execute command: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as ex:
            cleanup(args, envs)
            sys.exit(ex.returncode)
        except Exception as ex:
            print(f"Error: {ex}")
            cleanup(args, envs)

        cleanup(args, envs)

    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"ERROR: {ex}")
    except SystemExit as ex:
        sys.exit(ex.code)
