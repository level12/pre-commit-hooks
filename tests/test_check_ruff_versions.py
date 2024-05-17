from pathlib import Path

from click.testing import CliRunner
from pre_commit_hooks.check_ruff_versions import get_versions, main


tests_dpath = Path(__file__).parent


def run_cli(*args):
    return CliRunner().invoke(main, args)


class TestCheckRuffVersions:
    def test_same(self, monkeypatch):
        start_at = tests_dpath / 'check-ruff-versions-same'

        pc, dev = get_versions(start_at)
        assert pc == dev

        monkeypatch.chdir(start_at)
        result = run_cli()
        assert result.exit_code == 0
        assert result.output == ''

    def test_different(self, monkeypatch):
        start_at = tests_dpath / 'check-ruff-versions-diff'

        pc, dev = get_versions(start_at)
        assert pc == '0.4.4'
        assert dev == '0.4.3'

        monkeypatch.chdir(start_at)
        result = run_cli()
        assert result.exit_code == 1
        assert result.output.strip() == ('pre-commit ruff: 0.4.4\ndev.txt ruff: 0.4.3')

    def test_ruff_missing_both(self, monkeypatch):
        start_at = tests_dpath / 'check-ruff-versions-missing'

        assert get_versions(start_at) == (None, None)

        monkeypatch.chdir(start_at)
        result = run_cli()
        assert result.exit_code == 1
        assert result.output == 'Both pre-commit and dev.txt are missing ruff\n'
