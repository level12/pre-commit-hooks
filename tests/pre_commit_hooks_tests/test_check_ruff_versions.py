from collections.abc import Iterable
from os import environ
from pathlib import Path
import shutil
import subprocess

from click.testing import CliRunner
from pre_commit.commands.try_repo import _repo_ref

from pre_commit_hooks.check_ruff_versions import Versions, main


tests_dpath = Path(__file__).parent
pkg_dpath = tests_dpath.parent.parent


def run_cli(*args):
    result = CliRunner().invoke(main, args, catch_exceptions=False)
    if result.exception:
        print('STDOUT', result.stdout)
    return result


def sub_run(
    *args,
    capture=False,
    returns: None | Iterable[int] = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    kwargs.setdefault('check', not bool(returns))
    capture = kwargs.setdefault('capture_output', capture)
    args = args + kwargs.pop('args', ())
    env = kwargs.pop('env', None)
    if env:
        kwargs['env'] = environ | env
    if capture:
        kwargs.setdefault('text', True)

    try:
        result = subprocess.run(args, **kwargs)
        if returns and result.returncode not in returns:
            raise subprocess.CalledProcessError(result.returncode, args[0])
        return result
    except subprocess.CalledProcessError as e:
        if capture:
            print('STDOUT', e.stdout)
            print('STDERR', e.stderr)
        raise


class TestCheckRuffVersions:
    def test_same(self):
        start_at = tests_dpath / 'check-ruff-versions-same'

        ver = Versions.at_repo(start_at)
        assert ver.pc == ver.proj

        result = run_cli('.pre-commit-config.yaml', '--repo-root', start_at)
        assert result.exit_code == 0
        assert result.output == ''

    def test_different(self):
        start_at = tests_dpath / 'check-ruff-versions-diff'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.4.4'
        assert ver.proj == '0.4.3'

        result = run_cli('requirements/dev.txt', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output.strip() == ('pre-commit ruff: 0.4.4\ndev.txt ruff: 0.4.3')

    def test_ruff_missing_both(self):
        start_at = tests_dpath / 'check-ruff-versions-missing'

        ver = Versions.at_repo(start_at)
        assert (ver.pc, ver.proj) == (None, None)

        result = run_cli('.pre-commit-config.yaml', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output == 'Both pre-commit and dev.txt are missing ruff\n'

    def test_pkg_in_sub_dir(self, tmp_path: Path):
        test_repo_dpath = tests_dpath / 'check-ruff-versions-pkg-in-sub-dir'

        tmp_repo_dpath = tmp_path / 'repo'
        shutil.copytree(test_repo_dpath, tmp_repo_dpath)

        clone_repo_dpath, clone_rev = _repo_ref(tmp_path.as_posix(), pkg_dpath, None)

        pcc_fpath = tmp_repo_dpath.joinpath('.pre-commit-config.yaml')
        pcc_yaml = pcc_fpath.read_text()
        pcc_yaml = pcc_yaml.format(crv_repo=clone_repo_dpath, crv_rev=clone_rev)
        pcc_fpath.write_text(pcc_yaml)

        sub_run('git', 'init', cwd=tmp_repo_dpath)
        sub_run('pre-commit', 'install', cwd=tmp_repo_dpath)
        sub_run('git', 'add', '.', cwd=tmp_repo_dpath)
        result = sub_run('pre-commit', cwd=tmp_repo_dpath, capture=True)

        assert result.returncode == 0
        assert (
            result.stdout.strip().splitlines()[-1]
            == 'check ruff versions......................................................Passed'
        )


class TestCheckRuffVersionsUV:
    def test_different(self):
        start_at = tests_dpath / 'check-ruff-versions-uv-diff'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.4.4'
        assert ver.proj == '0.9.7'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output.strip() == ('pre-commit ruff: 0.4.4\nuv.lock ruff: 0.9.7')

    def test_same(self):
        start_at = tests_dpath / 'check-ruff-versions-uv-same'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.9.7'
        assert ver.proj == '0.9.7'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 0
        assert result.output.strip() == ''

    def test_lock_missing(self):
        start_at = tests_dpath / 'check-ruff-versions-uv-lock-missing'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output.strip() == ('pre-commit ruff: 0.9.7\nuv.lock ruff: None')
