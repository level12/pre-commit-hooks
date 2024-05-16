from pathlib import Path

import click
import pip_requirements_parser as prp
import yaml


pre_commit_gh_repo = 'https://github.com/charliermarsh/ruff-pre-commit'


def pre_commit_version(pc_yaml: Path):
    with pc_yaml.open() as fo:
        data = yaml.safe_load(fo)
        for repo in data['repos']:
            if repo['repo'] == pre_commit_gh_repo:
                return repo.get('rev', None)
    return None


def dev_version(dev_txt: Path):
    req = prp.RequirementsFile.from_file(dev_txt)
    ruff_req = [line for line in req.requirements if line.req.name.lower() == 'ruff']

    assert False


def check_versions(start_at: Path):
    pc = pre_commit_version(start_at / '.pre-commit-config.yaml')
    dev = dev_version(start_at / 'requirements' / 'dev.txt')
    print(pc)
    print(dev)


@click.command()
@click.argument('filenames', nargs=-1)
def main(filenames):
    pass
