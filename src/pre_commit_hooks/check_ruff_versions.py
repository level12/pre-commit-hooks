from dataclasses import dataclass
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


@dataclass
class Versions:
    pc: str
    proj: str
    is_uv: bool

    @property
    def proj_fname(self):
        return 'uv.lock' if self.is_uv else 'dev.txt'

    @classmethod
    def at_repo(cls, repo_dpath: Path, package_dpath: Path | None = None):
        package_dpath = package_dpath or repo_dpath

        assert repo_dpath.exists(), repo_dpath
        assert package_dpath.exists(), package_dpath

        uv_lock_path = package_dpath / 'uv.lock'
        is_uv_proj = uv_lock_path.exists()

        dev_version = (
            dev_version_uv(uv_lock_path)
            if is_uv_proj
            else dev_version_txt(package_dpath / 'requirements' / 'dev.txt')
        )
        return Versions(
            pre_commit_version(repo_dpath / '.pre-commit-config.yaml'),
            dev_version,
            is_uv_proj,
        )


@click.command()
@click.argument('file_paths', nargs=-1)
# pre-commit always calls from the root of the git directory, but give tests an option.
@click.option(
    '--repo-root',
    type=click.Path(path_type=Path, file_okay=False, exists=True),
    default=Path.cwd(),
)
@click.option('--package', 'packages', multiple=True)
@click.pass_context
def main(ctx: click.Context, file_paths: list[str], repo_root: Path, packages: list[str]):
    fail = False

    if not packages:
        packages = [None]

    if not repo_root.exists():
        ctx.fail('The repo root must exist:', repo_root)

    for package in packages:
        package_dpath = repo_root / package if package else None
        ver = Versions.at_repo(repo_root, package_dpath)
        if ver.pc != ver.proj:
            print('pre-commit ruff:', ver.pc)
            print(f'{ver.proj_fname} ruff:', ver.proj)
            fail = True
        elif (ver.pc, ver.proj) == (None, None):
            print(f'Both pre-commit and {ver.proj_fname} are missing ruff')
            fail = True

    if fail:
        sys.exit(1)
