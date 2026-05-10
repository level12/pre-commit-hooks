from collections.abc import Iterable
from os import environ
from pathlib import Path
import re
import shutil
import subprocess

from click.testing import CliRunner
import yaml

from pre_commit_hooks.check_ruff_versions import Versions, _ruff_version, main


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


def shadow_repo_ref(tmp_dpath: Path, repo_dpath: Path) -> tuple[Path, str]:
    # Adapted from pre_commit.commands.try_repo._repo_ref for this test's local snapshot use case.
    ref = sub_run('git', 'rev-parse', 'HEAD', cwd=repo_dpath, capture=True).stdout.strip()
    has_diff = sub_run('git', 'diff', '--quiet', 'HEAD', cwd=repo_dpath, returns=(0, 1))
    if has_diff.returncode == 0:
        return repo_dpath, ref

    shadow_dpath = tmp_dpath / 'shadow-repo'
    sub_run('git', 'clone', repo_dpath, shadow_dpath)
    sub_run('git', 'checkout', ref, '-b', '_pc_tmp', cwd=shadow_dpath)

    shadow_git_dpath = shadow_dpath / '.git'
    shadow_env = {
        'GIT_INDEX_FILE': (shadow_git_dpath / 'index').as_posix(),
        'GIT_OBJECT_DIRECTORY': (shadow_git_dpath / 'objects').as_posix(),
    }
    staged_files = (
        sub_run(
            'git',
            'diff',
            '--cached',
            '--name-only',
            cwd=repo_dpath,
            capture=True,
        )
        .stdout.strip()
        .splitlines()
    )
    if staged_files:
        sub_run('git', 'add', '--', *staged_files, cwd=repo_dpath, env=shadow_env)
    sub_run('git', 'add', '-u', cwd=repo_dpath, env=shadow_env)
    sub_run(
        'git',
        '-c',
        'user.name=pre-commit-hooks tests',
        '-c',
        'user.email=pre-commit-hooks@example.invalid',
        'commit',
        '--no-gpg-sign',
        '-m',
        'Temporary snapshot for tests',
        cwd=shadow_dpath,
    )
    ref = sub_run('git', 'rev-parse', 'HEAD', cwd=shadow_dpath, capture=True).stdout.strip()
    return shadow_dpath, ref


class TestRuffVersion:
    def test_finds_and_normalizes(self):
        assert _ruff_version([]) is None
        assert _ruff_version([{'repo': 'local', 'rev': 'v9.9.9'}]) is None
        assert _ruff_version([{'repo': 'https://github.com/astral-sh/ruff-pre-commit'}]) is None
        assert (
            _ruff_version([{'repo': 'https://github.com/astral-sh/ruff-pre-commit', 'rev': ''}])
            is None
        )
        assert (
            _ruff_version(
                [{'repo': 'https://github.com/astral-sh/ruff-pre-commit', 'rev': 'v1.2.3'}],
            )
            == '1.2.3'
        )
        assert (
            _ruff_version(
                [{'repo': 'https://github.com/astral-sh/ruff-pre-commit', 'rev': '1.2.3'}],
            )
            == '1.2.3'
        )


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

    def test_yml_config(self):
        start_at = tests_dpath / 'check-ruff-versions-yml'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.9.7'
        assert ver.pc_label == 'pre-commit'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 0
        assert result.output.strip() == ''

    def test_pkg_in_sub_dir(self, tmp_path: Path):
        test_repo_dpath = tests_dpath / 'check-ruff-versions-pkg-in-sub-dir'

        tmp_repo_dpath = tmp_path / 'repo'
        shutil.copytree(test_repo_dpath, tmp_repo_dpath)

        clone_repo_dpath, clone_rev = shadow_repo_ref(tmp_path, pkg_dpath)

        pcc_fpath = tmp_repo_dpath.joinpath('.pre-commit-config.yaml')
        pcc_yaml = pcc_fpath.read_text()
        pcc_yaml = pcc_yaml.replace('{crv_repo}', clone_repo_dpath.as_posix())
        pcc_yaml = pcc_yaml.replace('{crv_rev}', clone_rev)
        pcc_fpath.write_text(pcc_yaml)

        result = run_cli('--repo-root', tmp_repo_dpath, '--package', 'some-pkg')
        assert result.exit_code == 0
        assert result.output == ''


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


class TestCheckRuffVersionsPrek:
    def test_same(self):
        start_at = tests_dpath / 'check-ruff-versions-prek-same'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.9.7'
        assert ver.pc_label == 'prek.toml'
        assert ver.proj == '0.9.7'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 0
        assert result.output.strip() == ''

    def test_toml_1_1(self):
        start_at = tests_dpath / 'check-ruff-versions-prek-toml-1-1'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.9.7'
        assert ver.pc_label == 'prek.toml'
        assert ver.proj == '0.9.7'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 0
        assert result.output.strip() == ''

    def test_different(self):
        start_at = tests_dpath / 'check-ruff-versions-prek-diff'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.4.4'
        assert ver.proj == '0.9.7'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output.strip() == ('prek.toml ruff: 0.4.4\nuv.lock ruff: 0.9.7')

    def test_prek_takes_precedence(self):
        start_at = tests_dpath / 'check-ruff-versions-prek-precedence'

        ver = Versions.at_repo(start_at)
        assert ver.pc == '0.4.4'
        assert ver.pc_label == 'prek.toml'

        result = run_cli('uv.lock', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output.strip() == ('prek.toml ruff: 0.4.4\nuv.lock ruff: 0.9.7')

    def test_ruff_missing_both(self):
        start_at = tests_dpath / 'check-ruff-versions-prek-missing'

        ver = Versions.at_repo(start_at)
        assert (ver.pc, ver.proj) == (None, None)
        assert ver.pc_label == 'prek.toml'

        result = run_cli('prek.toml', '--repo-root', start_at)
        assert result.exit_code == 1
        assert result.output == 'Both prek.toml and dev.txt are missing ruff\n'


class TestHookManifest:
    def test_matches_prek_toml(self):
        hook = yaml.safe_load(pkg_dpath.joinpath('.pre-commit-hooks.yaml').read_text())[0]

        assert re.search(hook['files'], 'prek.toml')
        assert re.search(hook['files'], '.pre-commit-config.yaml')
        assert re.search(hook['files'], '.pre-commit-config.yml')
        assert re.search(hook['files'], 'path/to/uv.lock')
        assert re.search(hook['files'], 'path/to/requirements/dev.txt')
        assert not re.search(hook['files'], 'subdir/prek.toml')
