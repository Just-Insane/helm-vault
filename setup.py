from setuptools import setup

setup(
   name='vault',
   version='0.3.0',
   description='Helm plugin for storing secrets in HashiCorp Vault',
   author='Just-Insane',
   author_email='justin@justin-tech.com',
   install_requires=['ruamel.yaml', 'hvac'], #external packages as dependencies
   classifiers=[
        "Programming Language :: Python :: 3",
        "LICENSE :: OSI APPROVED :: GNU GENERAL PUBLIC LICENSE V3 (GPLV3)",
        "Operating System :: OS Independent",
    ],
)
