from pathlib import Path

from click.testing import CliRunner
from pre_commit_hooks.check_ruff_versions import check_versions, main


tests_dpath = Path(__file__).parent


class TestCheckRuffVersions:
    def test_same(self):
        assert check_versions(tests_dpath / 'check-ruff-versions-same')


# def test_hello_world():
#     runner = CliRunner()
#     result = runner.invoke(main, ['Peter'])
#     assert result.exit_code == 0
#     assert result.output == 'Hello Peter!\n'
