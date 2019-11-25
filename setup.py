from setuptools import setup, find_namespace_packages

with open('requirements.txt') as f:
    REQUIREMENTS = f.read()

setup(
    name='bluffer',
    version='1.0.0',
    install_requires=REQUIREMENTS,
    packages=find_namespace_packages(include=['bluffer*']),
)
