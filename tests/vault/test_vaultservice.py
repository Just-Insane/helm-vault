#!/usr/bin/env python3

import pytest
import hvac
import os
import logging

class Vault:
    def __init__(self):
        self.mount_path = "secret"
        self.secret_path = "hello"
        self.client = hvac.Client(url=os.environ["VAULT_ADDR"], token=os.environ["VAULT_TOKEN"])

    def vault_write(self, writevalue):
        self.client.secrets.kv.v2.create_or_update_secret(
            path=self.secret_path,
            secret=dict(value=writevalue),
        )

    def vault_read(self, readvalue):
        secret_version_response = self.client.secrets.kv.v2.read_secret_version(
            path=self.secret_path,
        )
        secret = secret_version_response.get("data", {}).get("data", {}).get("value")
        assert secret == readvalue


def test_main():
    vault = Vault()
    vault.vault_write("testsecret")
    vault.vault_read("testsecret")