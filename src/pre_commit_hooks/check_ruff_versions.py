from pathlib import Path
import sys

import click
import pip_requirements_parser as prp
import yaml


pre_commit_gh_repo = 'https://github.com/charliermarsh/ruff-pre-commit'


def pre_commit_version(pc_yaml: Path):
    with pc_yaml.open() as fo:
        data = yaml.safe_load(fo)
        for repo in data['repos']:
            if repo['repo'] == pre_commit_gh_repo:
                return repo.get('rev', '').replace('v', '', 1)
    return None


def dev_version(dev_txt: Path):
    req_file = prp.RequirementsFile.from_file(dev_txt)
    try:
        ruff_req = next(
            iter(line.req for line in req_file.requirements if line.req.name.lower() == 'ruff'),
        )
        return str(ruff_req.specifier).replace('==', '', 1)
    except StopIteration:
        return


def get_versions(start_at: Path):
    return (
        pre_commit_version(start_at / '.pre-commit-config.yaml'),
        dev_version(start_at / 'requirements' / 'dev.txt'),
    )


@click.command()
@click.argument('filenames', nargs=-1)
def main(filenames):
    start_at = Path.cwd()
    filename = filenames[0]

    if filename.endswith('.pre-commit-config.yaml'):
        start_at = start_at.joinpath(filename).parent
    else:
        # It must be the dev.txt requirements file
        start_at = start_at.joinpath(filename).parent.parent

    pc, dev = get_versions(start_at)

    if pc != dev:
        print('pre-commit ruff:', pc)
        print('dev.txt ruff:', dev)
        sys.exit(1)
    elif (pc, dev) == (None, None):
        print('Both pre-commit and dev.txt are missing ruff')
        sys.exit(1)
