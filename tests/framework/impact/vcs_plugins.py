"""VCS (Version Control System) plugins for change detection.

Change detection is abstracted into plugins so the impact analyzer can work with:
- Git (most common)
- Mercurial (hg)
- Perforce (p4)
- File modification time (local dev)
- Manual change specification (testing)
"""

import subprocess
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Set, List, Optional
from datetime import datetime


@dataclass
class Change:
    """Represents a file change."""
    file_path: str              # Path to changed file
    changed_lines: Set[int]     # Line numbers that changed
    change_type: str            # 'modified', 'added', 'deleted'


class VcsPlugin(ABC):
    """Abstract base class for version control system plugins."""
    
    @abstractmethod
    def get_diff(self, options: str = "") -> str:
        """
        Get diff output representing changes.
        
        Args:
            options: VCS-specific options (e.g., "--cached" for git)
        
        Returns:
            Diff output as string
        
        Raises:
            VcsPluginError: If VCS operation fails
        """
        pass
    
    @abstractmethod
    def get_changed_files(self, options: str = "") -> List[str]:
        """
        Get list of changed files.
        
        Args:
            options: VCS-specific options
        
        Returns:
            List of file paths that changed
        """
        pass
    
    def get_vcs_name(self) -> str:
        """Return VCS name (e.g., 'git', 'hg', 'p4')."""
        class_name = self.__class__.__name__
        # GitPlugin → git, HgPlugin → hg, etc.
        vcs_name = class_name.replace('Plugin', '').lower()
        return vcs_name


class VcsPluginError(Exception):
    """Raised when VCS plugin encounters an error."""
    pass


class GitPlugin(VcsPlugin):
    """Git version control system plugin."""
    
    def __init__(self, working_dir: str = '.'):
        self.working_dir = working_dir
    
    def get_diff(self, options: str = "--cached") -> str:
        """
        Get git diff output.
        
        Args:
            options: git diff options (default: --cached for staged changes)
                    Examples: "--unstaged", "--head", "--head~1..head"
        
        Returns:
            Full git diff output
        """
        try:
            cmd = ['git', 'diff'] + options.split()
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise VcsPluginError(f"git diff failed: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise VcsPluginError("git diff timed out")
        except Exception as e:
            raise VcsPluginError(f"git diff error: {e}")
    
    def get_changed_files(self, options: str = "--cached") -> List[str]:
        """
        Get list of changed files.
        
        Args:
            options: git diff options
        
        Returns:
            List of file paths
        """
        import re
        
        diff = self.get_diff(options)
        files = set()
        
        for line in diff.split('\n'):
            if line.startswith('+++ b/'):
                file_path = line[6:]
                files.add(file_path)
        
        return sorted(files)
    
    def get_status(self) -> dict:
        """
        Get git status information.
        
        Returns:
            Dict with staged, unstaged, untracked files
        """
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.working_dir,
                capture_output=True,
                text=True
            )
            
            staged = []
            unstaged = []
            untracked = []
            
            for line in result.stdout.split('\n'):
                if not line:
                    continue
                status = line[:2]
                file_path = line[3:]
                
                if status[0] in 'MADRC':
                    staged.append(file_path)
                if status[1] == 'M':
                    unstaged.append(file_path)
                if status == '??':
                    untracked.append(file_path)
            
            return {
                'staged': staged,
                'unstaged': unstaged,
                'untracked': untracked,
            }
        except Exception as e:
            raise VcsPluginError(f"git status error: {e}")


class HgPlugin(VcsPlugin):
    """Mercurial (Hg) version control system plugin."""
    
    def __init__(self, working_dir: str = '.'):
        self.working_dir = working_dir
    
    def get_diff(self, options: str = "") -> str:
        """
        Get hg diff output.
        
        Args:
            options: hg diff options (e.g., "-r . -r .^")
        
        Returns:
            Full hg diff output
        """
        try:
            cmd = ['hg', 'diff'] + options.split()
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise VcsPluginError(f"hg diff failed: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise VcsPluginError("hg diff timed out")
        except Exception as e:
            raise VcsPluginError(f"hg diff error: {e}")
    
    def get_changed_files(self, options: str = "") -> List[str]:
        """Get list of changed files via hg status."""
        try:
            result = subprocess.run(
                ['hg', 'status', '-m', '-a', '-r', '-d'],
                cwd=self.working_dir,
                capture_output=True,
                text=True
            )
            
            files = []
            for line in result.stdout.split('\n'):
                if line and len(line) > 2:
                    file_path = line[2:]
                    files.append(file_path)
            
            return sorted(files)
        except Exception as e:
            raise VcsPluginError(f"hg status error: {e}")


class P4Plugin(VcsPlugin):
    """Perforce (P4) version control system plugin."""
    
    def __init__(self, working_dir: str = '.'):
        self.working_dir = working_dir
    
    def get_diff(self, options: str = "") -> str:
        """
        Get p4 diff output.
        
        Args:
            options: p4 diff options (e.g., "-du" for unified diff)
        
        Returns:
            Full p4 diff output
        """
        try:
            cmd = ['p4', 'diff'] + options.split()
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            # p4 diff returns 0 even if there are changes
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            raise VcsPluginError("p4 diff timed out")
        except Exception as e:
            raise VcsPluginError(f"p4 diff error: {e}")
    
    def get_changed_files(self, options: str = "") -> List[str]:
        """Get list of opened files in p4."""
        try:
            result = subprocess.run(
                ['p4', 'opened'],
                cwd=self.working_dir,
                capture_output=True,
                text=True
            )
            
            files = []
            for line in result.stdout.split('\n'):
                if line:
                    # Format: //depot/path/file#1 - edit default change
                    parts = line.split('#')
                    if parts:
                        file_path = parts[0].strip()
                        files.append(file_path)
            
            return sorted(files)
        except Exception as e:
            raise VcsPluginError(f"p4 opened error: {e}")


class FileMtimePlugin(VcsPlugin):
    """File modification time based change detection (local development)."""
    
    def __init__(self, working_dir: str = '.', baseline_timestamp: Optional[float] = None):
        """
        Initialize file mtime plugin.
        
        Args:
            working_dir: Root directory to scan
            baseline_timestamp: Unix timestamp of baseline (if None, uses current time)
        """
        self.working_dir = working_dir
        self.baseline_timestamp = baseline_timestamp or os.path.getmtime('.')
    
    def get_diff(self, options: str = "") -> str:
        """
        Get pseudo-diff based on file modification times.
        
        Returns a simplified diff format showing which files changed.
        """
        changed_files = self.get_changed_files()
        
        lines = []
        for file_path in changed_files:
            mtime = os.path.getmtime(file_path)
            lines.append(f"Modified: {file_path} (timestamp: {mtime})")
        
        return '\n'.join(lines)
    
    def get_changed_files(self, options: str = "") -> List[str]:
        """
        Get files modified after baseline timestamp.
        
        Args:
            options: Unused (for interface compatibility)
        
        Returns:
            List of recently modified files
        """
        changed_files = []
        
        for dirpath, dirnames, filenames in os.walk(self.working_dir):
            # Skip common directories
            skip_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv'}
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    mtime = os.path.getmtime(file_path)
                    if mtime > self.baseline_timestamp:
                        changed_files.append(file_path)
                except OSError:
                    pass  # Skip inaccessible files
        
        return sorted(changed_files)


class ManualPlugin(VcsPlugin):
    """Manual change specification (for testing and CI automation)."""
    
    def __init__(self, changed_files: List[str] = None, changed_lines: dict = None):
        """
        Initialize manual plugin with explicit changes.
        
        Args:
            changed_files: List of file paths that changed
            changed_lines: Dict mapping file paths to sets of changed line numbers
        """
        self.changed_files = changed_files or []
        self.changed_lines = changed_lines or {}
    
    def get_diff(self, options: str = "") -> str:
        """Return a pseudo-diff with manually specified changes."""
        lines = []
        
        for file_path in self.changed_files:
            lines.append(f"diff --git a/{file_path} b/{file_path}")
            lines.append(f"+++ b/{file_path}")
            
            if file_path in self.changed_lines:
                for line_num in sorted(self.changed_lines[file_path]):
                    lines.append(f"Line {line_num}: modified")
        
        return '\n'.join(lines)
    
    def get_changed_files(self, options: str = "") -> List[str]:
        """Return the manually specified changed files."""
        return sorted(self.changed_files)
    
    def add_change(self, file_path: str, line_numbers: Set[int] = None):
        """Add a changed file to the manual specification."""
        if file_path not in self.changed_files:
            self.changed_files.append(file_path)
        
        if line_numbers:
            self.changed_lines[file_path] = line_numbers
