#!/usr/bin/env python3

import pytest
import src.vault as vault
import ruamel.yaml
import hvac
import os
import argparse
from argparse import RawTextHelpFormatter
import glob
import sys
import git
import platform
from datadiff.tools import assert_equal
from collections import OrderedDict as ordereddict
import mock
from shutil import copyfile
import subprocess

def test_load_yaml():

    data_test = ordereddict([('image', ordereddict([('repository', 'nextcloud'), ('tag', '15.0.2-apache'), ('pullPolicy', 'IfNotPresent')])), ('nameOverride', ''), ('fullnameOverride', ''), ('replicaCount', 1), ('ingress', ordereddict([('enabled', True), ('annotations', ordereddict())])), ('nextcloud', ordereddict([('host', 'nextcloud.corp.justin-tech.com'), ('username', 'admin'), ('password', 'changeme')])), ('internalDatabase', ordereddict([('enabled', True), ('name', 'nextcloud')])), ('externalDatabase', ordereddict([('enabled', False), ('host', None), ('user', 'VAULT:/secrets/testdata/user'), ('password', None), ('database', 'nextcloud')])), ('mariadb', ordereddict([('enabled', True), ('db', ordereddict([('name', 'nextcloud'), ('user', 'nextcloud'), ('password', 'changeme')])), ('persistence', ordereddict([('enabled', True), ('storageClass', 'nfs-client'), ('accessMode', 'ReadWriteOnce'), ('size', '8Gi')]))])), ('service', ordereddict([('type', 'ClusterIP'), ('port', 8080), ('loadBalancerIP', 'nil')])), ('persistence', ordereddict([('enabled', True), ('storageClass', 'nfs-client'), ('accessMode', 'ReadWriteOnce'), ('size', '8Gi')])), ('resources', ordereddict()), ('nodeSelector', ordereddict()), ('tolerations', []), ('affinity', ordereddict())])

    yaml_file = "./tests/test.yaml"
    data = vault.load_yaml(yaml_file)
    assert_equal(data, data_test)

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
    input_values = ["adfs1", "adfs2", "adfs3"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda s : output.append(s)

    vault.main(['enc', './tests/test.yaml'])

    assert output == [
        'Input a value for /nextcloud/password: ',
        'Input a value for /externalDatabase/user: ',
        'Input a value for /mariadb/db/password: ',
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

@pytest.mark.skipif(subprocess.run("helm", shell=True), reason="No way of testing without Helm")
def test_install():
    os.environ["KVVERSION"] = "v2"
    input_values = []
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda  s : output.append(s)

    vault.main(['install', 'stable/nextcloud --name nextcloud --namespace nextcloud -f ../tests/test.yaml --dry-run'])

    assert output == [
        'NAME:   nextcloud',
    ]
