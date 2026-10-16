"""
Test process substitution support with various flag combinations.

Process substitution like <(command) creates a file descriptor path /dev/fd/N
that argparse used to reject when flags and positional arguments were intermixed.
This test ensures the fix (using parse_intermixed_args) works correctly.
"""

import subprocess
import tempfile
import os


def run_grepnet(*args, input_text=None):
    """Run grepnet with given arguments and return (stdout, stderr, exit_code)."""
    cmd = ['grepnet'] + list(args)
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return '', 'TIMEOUT', -1


def test_process_substitution_basic():
    """Test basic process substitution without flags."""
    # This works even without the fix
    cmd = "bash -c 'grepnet 10.1.0.0/16 <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert '10.1.0.0/16' in result.stdout
    assert result.returncode == 0


def test_process_substitution_with_context_flag_after_pattern():
    """Test process substitution with -C flag after pattern (previously failed)."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -C 5 <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    # Should not error with "unrecognized arguments: /dev/fd/63"
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert '192.168.0.0/16' in result.stdout
    assert result.returncode == 0


def test_process_substitution_with_context_flag_before_pattern():
    """Test process substitution with -C flag before pattern."""
    cmd = "bash -c 'grepnet -C 5 10.1.0.0/16 <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert '192.168.0.0/16' in result.stdout
    assert result.returncode == 0


def test_process_substitution_multiple_files():
    """Test multiple process substitutions with flags in between."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -C 3 <(printf \"10.1.0.0/16\\n192.168.0.0/16\") <(printf \"10.0.0.0/8\\n10.1.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert '10.0.0.0/8' in result.stdout
    assert result.returncode == 0


def test_process_substitution_with_invert_flag():
    """Test process substitution with -v flag after pattern."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -v <(printf \"192.168.0.0/16\\n10.2.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    # -v should return lines that don't match
    assert '192.168.0.0/16' in result.stdout
    assert '10.2.0.0/16' in result.stdout
    assert '10.1.0.0/16' not in result.stdout
    assert result.returncode == 0


def test_process_substitution_with_only_matching():
    """Test process substitution with -o flag after pattern."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -o <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    # Only matching should extract the network, not the full line
    assert result.stdout.count('10.1.0.0/16') == 1
    assert result.returncode == 0


def test_process_substitution_with_line_number():
    """Test process substitution with -n flag after pattern."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -n <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert ':' in result.stdout  # Line numbers are formatted as line:content
    assert result.returncode == 0


def test_process_substitution_with_multiple_flags():
    """Test process substitution with multiple flags mixed in."""
    cmd = "bash -c 'grepnet 10.1.0.0/16 -n -C 2 <(printf \"10.1.0.0/16\\n192.168.0.0/16\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert result.returncode == 0


def test_process_substitution_mixed_with_regular_files():
    """Test mixing process substitution and regular files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('10.0.0.0/8\n10.1.0.0/16')
        regular_file = f.name
    
    try:
        cmd = f"bash -c 'grepnet 10.1.0.0/16 -H {regular_file} -C 1 <(printf \"192.168.0.0/16\\n10.1.0.0/16\")'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert 'unrecognized arguments' not in result.stderr
        assert '10.1.0.0/16' in result.stdout
        assert result.returncode == 0
    finally:
        os.unlink(regular_file)


def test_process_substitution_with_patterns_file():
    """Test process substitution with -f patterns file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('10.1.0.0/16\n192.168.0.0/16')
        patterns_file = f.name
    
    try:
        cmd = f"bash -c 'grepnet -f {patterns_file} -C 2 <(printf \"10.1.0.0/16\\n10.0.0.0/8\")'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert 'unrecognized arguments' not in result.stderr
        assert '10.1.0.0/16' in result.stdout
        assert result.returncode == 0
    finally:
        os.unlink(patterns_file)


def test_regular_arguments_still_work():
    """Ensure regular file argument parsing still works after parse_intermixed_args."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('10.1.0.0/16\n192.168.0.0/16')
        regular_file = f.name
    
    try:
        # Test traditional grep-like syntax: pattern file
        stdout, stderr, code = run_grepnet('10.1.0.0/16', regular_file)
        assert code == 0
        assert '10.1.0.0/16' in stdout
        
        # Test with flags before file
        stdout, stderr, code = run_grepnet('-n', '-C', '1', '10.1.0.0/16', regular_file)
        assert code == 0
        assert '10.1.0.0/16' in stdout
        
        # Test with flags after file (also works now with parse_intermixed_args)
        stdout, stderr, code = run_grepnet('10.1.0.0/16', regular_file, '-n', '-C', '1')
        assert code == 0
        assert '10.1.0.0/16' in stdout
    finally:
        os.unlink(regular_file)


def test_stdin_still_works():
    """Ensure stdin input still works after parse_intermixed_args."""
    input_data = '10.1.0.0/16\n192.168.0.0/16\n10.0.0.0/8'
    stdout, stderr, code = run_grepnet('10.1.0.0/16', input_text=input_data)
    assert code == 0
    assert '10.1.0.0/16' in stdout
    assert stdout.count('10.1.0.0/16') == 1


def test_multiple_patterns_with_process_substitution():
    """Test multiple -P pattern flags with process substitution."""
    cmd = "bash -c 'grepnet -P 10.1.0.0/16 -P 192.168.0.0/16 -C 1 <(printf \"10.1.0.0/16\\n192.168.0.0/16\\n10.0.0.0/8\")'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    assert 'unrecognized arguments' not in result.stderr
    assert '10.1.0.0/16' in result.stdout
    assert '192.168.0.0/16' in result.stdout
    assert result.returncode == 0
