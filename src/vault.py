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

VAULT_PATH_POSITION = 0 
VAULT_TEMPLATE_POSITION = 4

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
    VAULT_ADDR:     (The HTTP address of Vault, for example, http://localhost:8200)
    VAULT_TOKEN:    (The token used to authenticate with Vault)
    """, formatter_class=RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Encrypt help
    encrypt = subparsers.add_parser("enc", help="Parse a YAML file and store user entered data in Vault")
    encrypt.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    encrypt.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    encrypt.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault) Default: \"secret/helm\"")
    encrypt.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    encrypt.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    encrypt.add_argument("-s", "--secret-file", type=str, help="File containing the secret for input. Must end in .yaml.dec")
    encrypt.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Decrypt help
    decrypt = subparsers.add_parser("dec", help="Parse a YAML file and retrieve values from Vault")
    decrypt.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    decrypt.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    decrypt.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    decrypt.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    decrypt.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    decrypt.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Clean help
    clean = subparsers.add_parser("clean", help="Remove decrypted files (in the current directory)")
    clean.add_argument("-f", "--file", type=str, help="The specific YAML file to be deleted, without .dec", dest="yaml_file")
    clean.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # View Help
    view = subparsers.add_parser("view", help="View decrypted YAML file")
    view.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    view.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    view.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    view.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    view.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    view.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Edit Help
    edit = subparsers.add_parser("edit", help="Edit decrypted YAML file. DOES NOT CLEAN UP AUTOMATICALLY.")
    edit.add_argument("yaml_file", type=str, help="The YAML file to be worked on")
    edit.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    edit.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    edit.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    edit.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    edit.add_argument("-e", "--editor", help="Editor name. Default: (Linux/MacOS) \"vi\" (Windows) \"notepad\"", const=True, nargs="?")
    edit.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Install Help
    install = subparsers.add_parser("install", help="Wrapper that decrypts YAML files before running helm install")
    install.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    install.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    install.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    install.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    install.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    install.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Template Help
    template = subparsers.add_parser("template", help="Wrapper that decrypts YAML files before running helm install")
    template.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    template.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    template.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    template.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    template.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    template.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Upgrade Help
    upgrade = subparsers.add_parser("upgrade", help="Wrapper that decrypts YAML files before running helm install")
    upgrade.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    upgrade.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    upgrade.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    upgrade.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    upgrade.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    upgrade.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Lint Help
    lint = subparsers.add_parser("lint", help="Wrapper that decrypts YAML files before running helm install")
    lint.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    lint.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    lint.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    lint.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    lint.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    lint.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    # Diff Help
    diff = subparsers.add_parser("diff", help="Wrapper that decrypts YAML files before running helm diff")
    diff.add_argument("-f", "--values", type=str, dest="yaml_file", help="The encrypted YAML file to decrypt on the fly")
    diff.add_argument("-d", "--deliminator", type=str, help="The secret deliminator used when parsing. Default: \"changeme\"")
    diff.add_argument("-vt", "--vaulttemplate", type=str, help="Substring with path to vault key instead of deliminator. Default: \"VAULT:\"")
    diff.add_argument("-vp", "--vaultpath", type=str, help="The Vault Path (secret mount location in Vault). Default: \"secret/helm\"")
    diff.add_argument("-kv", "--kvversion", choices=['v1', 'v2'], default='v1', type=str, help="The KV Version (v1, v2) Default: \"v1\"")
    diff.add_argument("-v", "--verbose", help="Verbose logs", const=True, nargs="?")

    return parser

class Git:
    def __init__(self, cwd):
        self.cwd = cwd

    def get_git_root(self):
        self.git_repo = git.Repo(self.cwd, search_parent_directories=True)
        self.git_root = self.git_repo.git.rev_parse("--show-toplevel")
        return self.git_root

class Envs:
    def __init__(self, args):
        self.args = args

    def get_envs(self):
        # Get environment variables or ask for input
        if "VAULT_PATH" in os.environ:
            secret_mount=os.environ["VAULT_PATH"]
            if self.args.verbose is True:
                print("The environment vault path is: " + secret_mount)
        else:
            if self.args.vaultpath:
                secret_mount = self.args.vaultpath
                if self.args.verbose is True:
                    print("The vault path is: " + secret_mount)
            else:
                secret_mount = "secret/helm"
                if self.args.verbose is True:
                    print("The default vault path is: " + secret_mount)

        if "SECRET_DELIM" in os.environ:
            deliminator=os.environ["SECRET_DELIM"]
            if self.args.verbose is True:
                print("The env deliminator is: " + deliminator)
        else:
            if self.args.deliminator:
                deliminator = self.args.deliminator
                if self.args.verbose is True:
                    print("The deliminator is: " + deliminator)
            else:
                deliminator = "changeme"
                if self.args.verbose is True:
                    print("The default deliminator is: " + deliminator)

        if "SECRET_TEMPLATE" in os.environ:
            vault_template=os.environ["SECRET_TEMPLATE"]
            if self.args.verbose is True:
                print("The env vault template is: " + vault_template)
        else:
            if self.args.vaulttemplate:
                vault_template = self.args.vaulttemplate
                if self.args.verbose is True:
                    print("The vault template is: " + vault_template)
            else:
                vault_template = "VAULT:"
                if self.args.verbose is True:
                    print("The default vault template is: " + vault_template)
        if "EDITOR" in os.environ:
            editor=os.environ["EDITOR"]
            if self.args.verbose is True:
                print("The env editor is: " + editor)
        else:
            try:
                editor = self.args.edit
                if self.args.verbose is True:
                    print("The editor is: " + editor)
            except AttributeError:
                if platform.system() != "Windows":
                    editor = "vi"
                    if self.args.verbose is True:
                        print("The default editor is: " + editor)
                else:
                    editor = "notepad"
                    if self.args.verbose is True:
                        print("The default editor is: " + editor)
            except Exception as ex:
                print(f"Error: {ex}")

        if "KVVERSION" in os.environ:
            kvversion=os.environ["KVVERSION"]
            if self.args.verbose is True:
                print("The env kvversion is: " + kvversion)
        else:
            if self.args.kvversion:
                kvversion = self.args.kvversion
                if self.args.verbose is True:
                    print("The kvversion is: " + kvversion)
            else:
                kvversion = "v1"
                if self.args.verbose is True:
                    print("The default kvversion is: " + kvversion)

        return secret_mount, deliminator, editor, kvversion, vault_template

class Vault:
    def __init__(self, args, envs):
        self.args = args
        self.envs = envs
        self.folder = Git(os.getcwd())
        self.folder = self.folder.get_git_root()
        self.folder = os.path.basename(self.folder)
        self.kvversion = envs[3]

        # Setup Vault client (hvac)
        try:
            self.client = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"])
        except KeyError:
            print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
        except Exception as ex:
            print(f"ERROR: {ex}")

    def vault_write(self, value, path, key, full_path=None):
        # Use path from template if presents
        if full_path is not None:
            _path = full_path
            if _path.startswith('/'):
                mount_point = _path.split('/')[1]
                _path = '/'.join(_path.split('/')[2:])
            else:
                mount_point = self.envs[VAULT_PATH_POSITION].split('/')[0]
        else:
            mount_point = None
            _path = f"{self.envs[0]}/{self.folder}{path}/{key}"


        # Write to vault, using the correct Vault KV version
        if self.kvversion == "v1":
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
            try:
                if mount_point is not None:
                    self.client.write(_path, value=value, mount_point = mount_point)
                else:
                    self.client.write(_path, value=value)
                if self.args.verbose is True:
                    print(f"Wrote {value} to: {_path}")
            except AttributeError:
                print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
            except Exception as ex:
                print(f"Error: {ex}")

        elif self.kvversion == "v2":
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
            try:
                if mount_point is not None:
                    self.client.secrets.kv.v2.create_or_update_secret(
                        path=_path,
                        secret=dict(value=value),
                        mount_point = mount_point,
                    )
                else:
                    self.client.secrets.kv.v2.create_or_update_secret(
                        path=_path,
                        secret=dict(value=value),
                    )                    
                if self.args.verbose is True:
                    print(f"Wrote {value} to: {_path}")
            except AttributeError:
                print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
            except Exception as ex:
                print(f"ERROR: {ex}")

        else:
            print("Wrong KV Version specified, either v1 or v2")


    def vault_read(self, value, path, key, full_path=None):
        # Use path from template if presents
        if full_path is not None:
            _path = full_path
            if _path.startswith('/'):
                mount_point = _path.split('/')[1]
                _path = '/'.join(_path.split('/')[2:])
            else:
                mount_point = self.envs[VAULT_PATH_POSITION].split('/')[0]
        else:
            mount_point = None
            _path = f"{self.envs[0]}/{self.folder}{path}/{key}"

        # Read from Vault, using the correct Vault KV version
        if self.kvversion == "v1":
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
            try:
                value = self.client.read(_path)
                if self.args.verbose is True:
                    print(f"Got {value} from: {_path}")
                return value.get("data", {}).get("value")
            except AttributeError as ex:
                print(f"Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables. {ex}")
            except Exception as ex:
                print(f"Error: {ex}")

        elif self.kvversion == "v2":
            if self.args.verbose is True:
                print(f"Using KV Version: {self.kvversion}")
            try:
                if mount_point is not None:
                    value = self.client.secrets.kv.v2.read_secret_version(
                        path=_path,
                        mount_point=mount_point,
                    )
                else:
                     value = self.client.secrets.kv.v2.read_secret_version(
                        path=_path,
                    )                   
                value = value.get("data", {}).get("data", {}).get("value")
                if self.args.verbose is True:
                    print(f"Got {value} from: {_path}")
                return value
            except AttributeError:
                print("Vault not configured correctly, check VAULT_ADDR and VAULT_TOKEN env variables.")
            except Exception as ex:
                print(f"ERROR: {ex}")

        else:
            print("Wrong KV Version specified, either v1 or v2")

def load_yaml(yaml_file):
    # Load the YAML file
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    with open(yaml_file) as filepath:
        data = yaml.load(filepath)
        return data

def cleanup(args):
    # Cleanup decrypted files
    yaml_file = args.yaml_file
    try:
        os.remove(f"{yaml_file}.dec")
        if args.verbose is True:
            print(f"Deleted {yaml_file}.dec")
            sys.exit()
    except AttributeError:
        for fl in glob.glob("*.dec"):
            os.remove(fl)
            if args.verbose is True:
                print(f"Deleted {fl}")
                sys.exit()
    except Exception as ex:
        print(f"Error: {ex}")
    else:
        sys.exit()

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
    path = path if path is not None else ""
    action = args.action
    if isinstance(data, dict):
        for key, value in data.items():
            if value == pattern or str(value).startswith(envs[VAULT_TEMPLATE_POSITION]):
                if value.startswith(envs[VAULT_TEMPLATE_POSITION]):
                    _full_path = value[len(envs[VAULT_TEMPLATE_POSITION]):]
                else:
                    _full_path = None
                if action == "enc":
                    if secret_data:
                        data[key] = value_from_path(secret_data, f"{path}/{key}")
                    else:
                        data[key] = input(f"Input a value for {path}/{key}: ")
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

    if action == "clean":
        cleanup(args)

    envs = Envs(args)
    envs = envs.get_envs()
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    secret_data = load_secret(args) if args.action == 'enc' else None

    for path, key, value in dict_walker(envs[1], data, args, envs, secret_data):
        print("Done")

    if action == "dec":
        yaml.dump(data, open(f"{yaml_file}.dec", "w"))
        print("Done Decrypting")
    elif action == "view":
        yaml.dump(data, sys.stdout)
    elif action == "edit":
        yaml.dump(data, open(f"{yaml_file}.dec", "w"))
        os.system(envs[2] + ' ' + f"{yaml_file}.dec")
    # These Helm commands are only different due to passed variables
    elif (action == "install") or (action == "template") or (action == "upgrade") or (action == "lint") or (action == "diff"):
        yaml.dump(data, open(f"{yaml_file}.dec", "w"))
        leftovers = ' '.join(leftovers)

        try:
            subprocess.run(f"helm {args.action} {leftovers} -f {yaml_file}.dec", shell=True)
        except Exception as ex:
            print(f"Error: {ex}")

        cleanup(args)

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"ERROR: {ex}")
    except SystemExit:
        pass