from pathlib import Path
import sys
import tomllib

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


def dev_version_txt(dev_txt: Path):
    req_file = prp.RequirementsFile.from_file(dev_txt)
    try:
        ruff_req = next(
            iter(line.req for line in req_file.requirements if line.req.name.lower() == 'ruff'),
        )
        return str(ruff_req.specifier).replace('==', '', 1)
    except StopIteration:
        return


def _find_package(packages: list[dict], name: str):
    for package in packages:
        if package['name'] == name:
            return package
    return None


def dev_version_uv(uv_lock: Path):
    with uv_lock.open('rb') as uv_fo:
        lock_data = tomllib.load(uv_fo)
    ruff = _find_package(lock_data['package'], 'ruff')
    if not ruff:
        return
    return ruff['version']


def get_versions(start_at: Path):
    uv_lock_path = start_at / 'uv.lock'
    dev_version = (
        dev_version_uv(uv_lock_path)
        if uv_lock_path.exists()
        else dev_version_txt(start_at / 'requirements' / 'dev.txt')
    )
    return (
        pre_commit_version(start_at / '.pre-commit-config.yaml'),
        dev_version,
    )


@click.command()
@click.argument('filenames', nargs=-1)
def main(filenames):
    start_at = Path.cwd()
    filename = filenames[0]

    if filename.endswith(('.pre-commit-config.yaml', 'uv.lock')):
        start_at = start_at.joinpath(filename).parent
    else:
        # It's a dev.txt
        start_at = start_at.joinpath(filename).parent.parent

    pc, dev = get_versions(start_at)

    if pc != dev:
        print('pre-commit ruff:', pc)
        print('dev.txt ruff:', dev)
        sys.exit(1)
    elif (pc, dev) == (None, None):
        print('Both pre-commit and dev.txt are missing ruff')
        sys.exit(1)
