from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib

import click
import pip_requirements_parser as prp
import tomlkit
import yaml


prek_fname = 'prek.toml'
pre_commit_fname = '.pre-commit-config.yaml'
pre_commit_alt_fname = '.pre-commit-config.yml'
pre_commit_fnames = (pre_commit_fname, pre_commit_alt_fname)
pre_commit_gh_repo = 'https://github.com/astral-sh/ruff-pre-commit'


def _ruff_version(repos: list[dict]) -> str | None:
    for repo in repos:
        if repo['repo'] == pre_commit_gh_repo:
            return repo.get('rev', '').removeprefix('v') or None
    return None


def pre_commit_version(pc_yaml: Path) -> str | None:
    with pc_yaml.open() as fo:
        data = yaml.safe_load(fo) or {}
    return _ruff_version(data.get('repos', []))


def load_prek_toml(prek_fpath: Path) -> dict:
    with prek_fpath.open('rb') as fo:
        return tomlkit.load(fo).unwrap()


def prek_version(prek_toml: Path) -> str | None:
    data = load_prek_toml(prek_toml)
    return _ruff_version(data.get('repos', []))


def project_config_version(repo_dpath: Path) -> tuple[str | None, str]:
    for fname in (prek_fname, *pre_commit_fnames):
        config_fpath = repo_dpath / fname
        if not config_fpath.exists():
            continue

        version = (
            prek_version(config_fpath) if fname == prek_fname else pre_commit_version(config_fpath)
        )
        return version, fname

    expected = ', '.join((prek_fname, *pre_commit_fnames))
    raise FileNotFoundError(f'No hook config found in {repo_dpath}; expected one of: {expected}')


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
    pc: str | None
    proj: str | None
    is_uv: bool
    pc_fname: str

    @property
    def pc_label(self) -> str:
        if self.pc_fname == prek_fname:
            return self.pc_fname
        return 'pre-commit'

    @property
    def proj_fname(self) -> str:
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
        pc_version, pc_fname = project_config_version(repo_dpath)
        return Versions(
            pc_version,
            dev_version,
            is_uv_proj,
            pc_fname,
        )


@click.command()
@click.argument('file_paths', nargs=-1, expose_value=False)
# pre-commit always calls from the root of the git directory, but give tests an option.
@click.option(
    '--repo-root',
    type=click.Path(path_type=Path, file_okay=False, exists=True),
    default=Path.cwd(),
)
@click.option('--package', 'packages', multiple=True)
@click.pass_context
def main(ctx: click.Context, repo_root: Path, packages: list[str]):
    fail = False

    if not packages:
        packages = [None]

    if not repo_root.exists():
        ctx.fail('The repo root must exist:', repo_root)

    for package in packages:
        package_dpath = repo_root / package if package else None
        ver = Versions.at_repo(repo_root, package_dpath)
        if ver.pc != ver.proj:
            print(f'{ver.pc_label} ruff:', ver.pc)
            print(f'{ver.proj_fname} ruff:', ver.proj)
            fail = True
        elif (ver.pc, ver.proj) == (None, None):
            print(f'Both {ver.pc_label} and {ver.proj_fname} are missing ruff')
            fail = True

    if fail:
        sys.exit(1)
