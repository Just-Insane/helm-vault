#!/usr/bin/env python3

import os
import subprocess
from collections import OrderedDict as ordereddict
from shutil import copyfile

import pytest
from datadiff.tools import assert_equal

import src.vault as vault

# Check if helm is installed
helm_available = None
if subprocess.call(['which', 'helm']) == 0:
    subprocess.call(['helm', 'repo', 'add', 'nextcloud', 'https://nextcloud.github.io/helm/'])
    subprocess.call(['helm', 'repo', 'update'])
    helm_available = True
else:
    helm_available = False

# Check if kubernetes is available and running
k8s_available = None
if subprocess.call(['which', 'kubectl']) == 0:
    if subprocess.call(['kubectl', 'cluster-info']) == 0:
        k8s_available = True
else:
    k8s_available = False

def test_load_yaml():

    data_test = ordereddict([('image', ordereddict([('repository', 'nextcloud'), ('tag', '15.0.2-apache'), ('pullPolicy', 'IfNotPresent')])), ('nameOverride', ''), ('fullnameOverride', ''), ('replicaCount', 1), ('ingress', ordereddict([('enabled', True), ('annotations', ordereddict())])), ('nextcloud', ordereddict([('host', 'nextcloud.corp.justin-tech.com'), ('username', 'admin'), ('password', 'changeme')])), ('internalDatabase', ordereddict([('enabled', True), ('name', 'nextcloud')])), ('externalDatabase', ordereddict([('enabled', False), ('host', None), ('user', 'VAULT:/secret/testdata/user'), ('password', 'VAULT:/secret/{environment}/testdata/password'), ('database', 'nextcloud')])), ('mariadb', ordereddict([('enabled', True), ('db', ordereddict([('name', 'nextcloud'), ('user', 'nextcloud'), ('password', 'changeme')])), ('persistence', ordereddict([('enabled', True), ('storageClass', 'nfs-client'), ('accessMode', 'ReadWriteOnce'), ('size', '8Gi')]))])), ('service', ordereddict([('type', 'ClusterIP'), ('port', 8080), ('loadBalancerIP', 'nil')])), ('persistence', ordereddict([('enabled', True), ('storageClass', 'nfs-client'), ('accessMode', 'ReadWriteOnce'), ('size', '8Gi')])), ('resources', ordereddict()), ('nodeSelector', ordereddict()), ('tolerations', []), ('affinity', ordereddict())])
    yaml_file = "./tests/test.yaml"
    data = vault.load_yaml(yaml_file)
    print(data)
    assert_equal(data, data_test)

def test_load_broken_yaml():
    broken_yaml_file = "./tests/broken.yaml"
    with pytest.raises(vault.ruamel.yaml.scanner.ScannerError):
        broken_data = vault.load_yaml(broken_yaml_file)
        print(broken_data)

def test_git_path():
    cwd = os.getcwd()
    git_path = vault.Git(cwd)
    git_path = git_path.get_git_root()
    assert git_path == os.getcwd()

def test_parser():
    copyfile("./tests/test.yaml", "./tests/test.yaml.bak")
    parser = vault.parse_args(['clean', '-f ./tests/test.yaml'])
    assert(parser)
    copyfile("./tests/test.yaml.bak", "./tests/test.yaml")
    os.remove("./tests/test.yaml.bak")

def filecheckfunc():
    raise FileNotFoundError

def test_enc():
    os.environ["KVVERSION"] = "v2"
    input_values = ["adfs1", "adfs2", "adfs3", "adfs4"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda s : output.append(s)

    vault.main(['enc', './tests/test.yaml'])

    assert output == [
        'Input a value for nextcloud.password: ',
        'Input a value for externalDatabase.user: ',
        'Input a value for externalDatabase.password: ',
        'Input a value for mariadb.db.password: ',
    ]

def test_enc_with_env():
    os.environ["KVVERSION"] = "v2"
    input_values = ["adfs1", "adfs2", "adfs3", "adfs4"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda s : output.append(s)

    vault.main(['enc', './tests/test.yaml', '-e', 'test'])

    assert output == [
        'Input a value for nextcloud.password: ',
        'Input a value for externalDatabase.user: ',
        'Input a value for externalDatabase.password: ',
        'Input a value for mariadb.db.password: ',
    ]

def test_refuse_enc_from_file_with_bad_name():
    with pytest.raises(Exception) as e:
        vault.main(['enc', './tests/test.yaml', '-s', './tests/test.yaml.bad'])
        assert "ERROR: Secret file name must end with" in str(e.value)

def test_enc_from_file():
    os.environ["KVVERSION"] = "v2"
    vault.main(['enc', './tests/test.yaml', '-s', './tests/test.yaml.dec'])
    assert True # If it reaches here without error then encoding was a success
    # TODO: Maybe test if the secret is correctly saved to vault


def test_enc_from_file_with_environment():
    os.environ["KVVERSION"] = "v2"
    vault.main(['enc', './tests/test.yaml', '-s', './tests/test.yaml.dec', '-e', 'test'])
    assert True # If it reaches here without error then encoding was a success
    # TODO: Maybe test if the secret is correctly saved to vault


def test_dec():
    os.environ["KVVERSION"] = "v2"
    input_values = ["adfs1", "adfs2"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda s : output.append(s)

    vault.main(['dec', './tests/test.yaml'])

    assert output == [
        'Done Decrypting',
    ]

def test_value_from_path():
    data = {
        "chapter1": {
            "chapter1.1": {
                "chapter1.1.1": "good",
                "chapter1.1.2": "bad",
            },
            "chapter1.2": {
                "chapter1.2.1": "good",
                "chapter1.2.2": "bad",
            }
        }
    }
    val = vault.value_from_path(data, "/")
    assert val == data
    val = vault.value_from_path(data, "/chapter1/chapter1.1")
    assert val == {
                "chapter1.1.1": "good",
                "chapter1.1.2": "bad",
            }
    val = vault.value_from_path(data, "/chapter1/chapter1.1/chapter1.1.2")
    assert val == "bad"

    with pytest.raises(Exception) as e:
        val = vault.value_from_path(data, "/chapter1/chapter1.1/bleh")
        assert "Missing secret value" in str(e.value)

def test_clean():
    os.environ["KVVERSION"] = "v2"
    copyfile("./tests/test.yaml.dec", "./tests/test.yaml.dec.bak")
    with pytest.raises(FileNotFoundError):
        vault.main(['clean', '-f .tests/test.yaml', '-v'])
    copyfile("./tests/test.yaml.dec.bak", "./tests/test.yaml.dec")
    os.remove("./tests/test.yaml.dec.bak")

@pytest.mark.skipif(not (helm_available and k8s_available), reason="No way of testing without Helm")
def test_install(capfd):
    os.environ["KVVERSION"] = "v2"
    # copy test values to prevent deletion of test.yaml.dec
    copyfile("./tests/test.yaml", "./tests/values.yaml")
    vault.main(['install', '-f', './tests/values.yaml', 'nextcloud nextcloud/nextcloud --namespace nextcloud --dry-run'])
    cap = capfd.readouterr()
    assert 'NAME: nextcloud' in cap.out.strip()
    os.remove("./tests/values.yaml")

@pytest.mark.skipif(not helm_available, reason="No way of testing without Helm")
def test_lint(capfd):
    os.environ["KVVERSION"] = "v2"
    # copy test values to prevent deletion of test.yaml.dec
    copyfile("./tests/test.yaml", "./tests/values.yaml")
    vault.main(['lint', '-f', './tests/values.yaml', './tests/helm/good_chart'])
    cap = capfd.readouterr()
    assert 'Linting ./tests/helm/good_chart' in cap.out.strip()
    os.remove("./tests/values.yaml")

@pytest.mark.skipif(not helm_available, reason="No way of testing without Helm")
def test_bad_lint():
    os.environ["KVVERSION"] = "v2"
    # copy test values to prevent deletion of test.yaml.dec
    copyfile("./tests/test.yaml", "./tests/values.yaml")
    with pytest.raises(SystemExit):
        vault.main(['lint', '-f', './tests/values.yaml', './tests/helm/bad_chart'])
    os.remove("./tests/values.yaml")
