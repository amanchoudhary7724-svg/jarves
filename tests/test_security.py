# Jarvi security regression tests - no file mutations, only assertions
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class TestDevToolsDefaults:
    def test_command_exec_default_false(self):
        from tools.dev_tools import AUTO
        assert AUTO is False

    def test_blocked_patterns_compiled(self):
        from tools.dev_tools import _BLOCKED_PATTERNS
        assert _BLOCKED_PATTERNS is not None
        assert _BLOCKED_PATTERNS.search('del /s C:' + chr(92) + 'test')
        assert _BLOCKED_PATTERNS.search('format c:' + chr(92) + 'test')
        assert _BLOCKED_PATTERNS.search('reg delete HKLM')
        assert _BLOCKED_PATTERNS.search('net user hacker pass')

    def test_shell_meta_compiled(self):
        from tools.dev_tools import _SHELL_META
        assert _SHELL_META.search('echo | findstr')
        assert _SHELL_META.search('a & b')
        assert not _SHELL_META.search('echo hello')

    def test_path_allowed_uses_roots(self):
        from tools.dev_tools import ALLOWED_WRITE_ROOTS, _is_path_allowed
        assert len(ALLOWED_WRITE_ROOTS) > 0
        assert _is_path_allowed(os.path.join(ALLOWED_WRITE_ROOTS[0], 'test.txt'))
        assert not _is_path_allowed('C:' + chr(92) + 'Windows' + chr(92) + 'System32' + chr(92) + 'test.txt')

    def test_run_command_disabled_returns_message(self):
        from tools import dev_tools
        r = dev_tools.run_command('echo hello')
        assert 'disabled' in r.lower()

    def test_write_file_blocks_system_path(self):
        from tools import dev_tools
        r = dev_tools.write_file('C:' + chr(92) + 'Windows' + chr(92) + 'System32' + chr(92) + 'test.txt', 'x')
        assert 'BLOCKED' in r

    def test_edit_file_blocks_system_path(self):
        from tools import dev_tools
        r = dev_tools.edit_file('C:' + chr(92) + 'Windows' + chr(92) + 'System32' + chr(92) + 'hosts', 'a', 'b')
        assert 'BLOCKED' in r


class TestPcControl:
    def test_failsafe_enabled(self):
        import pyautogui
        assert pyautogui.FAILSAFE is True

    def test_critical_processes_defined(self):
        from tools.pc_control import _CRITICAL_PROCESSES
        assert len(_CRITICAL_PROCESSES) > 0
        for name in ['explorer', 'svchost', 'csrss', 'lsass']:
            assert name in _CRITICAL_PROCESSES, f'{name} should be in blocklist'

    def test_kill_process_blocks_critical(self):
        from tools import pc_control
        for name in ['explorer', 'svchost', 'csrss', 'system']:
            r = pc_control.kill_process(name)
            assert 'BLOCKED' in r, f'kill_process({name!r}) should be blocked, got: {r}'


class TestOfflineTools:
    def test_close_app_blocks_critical(self):
        from tools import offline_tools
        for name in ['explorer', 'svchost', 'csrss']:
            r = offline_tools.close_app(name)
            assert 'BLOCKED' in r, f'close_app({name!r}) should be blocked, got: {r}'


class TestConfigLoader:
    def test_env_placeholder_resolution(self):
        from config_loader import _resolve_env_placeholders
        os.environ['JARVIS_TEST_42'] = 'hello'
        try:
            result = _resolve_env_placeholders('__ENV:JARVIS_TEST_42__')
            assert result == 'hello', f'Expected hello, got {result!r}'
        finally:
            del os.environ['JARVIS_TEST_42']

    def test_env_nested_dict(self):
        from config_loader import _resolve_env_placeholders
        os.environ['JARVIS_TEST_43'] = 'secret'
        try:
            data = {'outer': {'key': '__ENV:JARVIS_TEST_43__'}}
            result = _resolve_env_placeholders(data)
            assert result['outer']['key'] == 'secret'
        finally:
            del os.environ['JARVIS_TEST_43']

    def test_non_placeholder_unchanged(self):
        from config_loader import _resolve_env_placeholders
        assert _resolve_env_placeholders('normal text') == 'normal text'
        assert _resolve_env_placeholders(42) == 42


class TestConfigJson:
    def test_api_key_is_placeholder(self):
        from config_loader import CFG
        key = CFG.get('nvidia_api_key', '')
        assert key.startswith('__ENV:') or key == ''

    def test_email_password_is_placeholder(self):
        from config_loader import CFG
        pw = CFG.get('email', {}).get('app_password', '')
        assert pw.startswith('__ENV:') or pw == ''

    def test_command_exec_disabled(self):
        from config_loader import CFG
        assert CFG.get('developer', {}).get('allow_command_exec') is False

    def test_confirm_destructive_enabled(self):
        from config_loader import CFG
        assert CFG.get('developer', {}).get('confirm_destructive') is True


class TestRegistryExecute:
    def test_unknown_tool(self):
        from tools.registry import execute
        r = execute('nonexistent_tool_xyz', {})
        assert 'exist nahi' in r

    def test_bad_args_gives_error(self):
        from tools.registry import execute
        r = execute('get_time', {'kind': 12345})
        assert isinstance(r, str) and len(r) > 0

    def test_valid_tool_returns_string(self):
        from tools.registry import execute
        r = execute('get_time', {'kind': 'time'})
        assert isinstance(r, str) and len(r) > 0


