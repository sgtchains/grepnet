#!/usr/bin/env python3
"""CLI tool for test impact analysis.

Example usage:
    # Show impact analysis (don't run tests)
    ./impact_cli.py --analyze
    
    # Show what changed
    ./impact_cli.py --diff
    
    # Run only affected tests
    ./impact_cli.py --run-affected
    
    # Show confidence scores
    ./impact_cli.py --analyze --show-scores
    
    # For unstaged changes
    ./impact_cli.py --analyze --unstaged
"""

import json
import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from framework.impact import ImpactAnalyzer, ImpactConfig


def main():
    parser = argparse.ArgumentParser(
        description='Test impact analysis - determine which tests to run based on code changes'
    )
    
    # Mode selection
    parser.add_argument(
        '--analyze',
        action='store_true',
        help='Show impact analysis without running tests'
    )
    parser.add_argument(
        '--diff',
        action='store_true',
        help='Show git diff of changed files'
    )
    parser.add_argument(
        '--run-affected',
        action='store_true',
        help='Run only affected tests'
    )
    parser.add_argument(
        '--run-all',
        action='store_true',
        help='Run all tests (for comparison)'
    )
    
    # Configuration
    parser.add_argument(
        '--language',
        default='python',
        help='Language to analyze (default: python)'
    )
    parser.add_argument(
        '--vcs',
        default='git',
        choices=['git', 'hg', 'p4', 'mtime', 'manual'],
        help='Version control system (default: git)'
    )
    parser.add_argument(
        '--staged',
        action='store_true',
        default=True,
        help='Analyze staged changes only (default)'
    )
    parser.add_argument(
        '--unstaged',
        action='store_true',
        help='Analyze unstaged changes'
    )
    parser.add_argument(
        '--cached',
        action='store_true',
        help='Analyze staged changes (same as --staged)'
    )
    parser.add_argument(
        '--working-dir',
        default='.',
        help='Root directory to analyze (default: current)'
    )
    
    # Output options
    parser.add_argument(
        '--show-scores',
        action='store_true',
        help='Show confidence scores for each test'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show only summary (default)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Verbose output'
    )
    
    # Test execution options
    parser.add_argument(
        '--parallel',
        type=int,
        metavar='N',
        help='Run N tests in parallel'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        metavar='SECONDS',
        help='Timeout per test'
    )
    
    args = parser.parse_args()
    
    # Default to --analyze if no mode specified
    if not (args.analyze or args.diff or args.run_affected or args.run_all):
        args.analyze = True
    
    try:
        # Create analyzer
        config = ImpactConfig(
            language=args.language,
            vcs_type=args.vcs,
            vcs_options='--unstaged' if args.unstaged else '--cached',
        )
        analyzer = ImpactAnalyzer(config=config, root_dir=args.working_dir)
        
        if args.diff:
            show_diff(args.working_dir)
        
        if args.analyze:
            report = analyzer.analyze_changes()
            show_analysis(report, args)
        
        if args.run_affected:
            report = analyzer.analyze_changes()
            run_affected_tests(report, args)
        
        if args.run_all:
            run_all_tests(args)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def show_diff(working_dir: str):
    """Show git diff output."""
    result = subprocess.run(
        ['git', 'diff', '--cached'],
        cwd=working_dir,
        capture_output=True,
        text=True
    )
    print(result.stdout)


def show_analysis(report, args):
    """Display impact analysis report."""
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return
    
    # Header
    print("\n" + "=" * 70)
    print("TEST IMPACT ANALYSIS")
    print("=" * 70)
    
    # Summary
    print(f"\n{report.summary}")
    print(f"  Changed files: {len(report.changed_files)}")
    print(f"  Changed functions: {len(report.changed_functions)}")
    print(f"  Estimated runtime: {report.execution_time_estimate:.1f}s")
    
    # Changed files
    if report.changed_files and args.verbose:
        print("\n📝 Changed Files:")
        for f in report.changed_files:
            print(f"  - {f}")
    
    # Changed functions
    if report.changed_functions and args.verbose:
        print("\n🔧 Changed Functions:")
        for func in report.changed_functions:
            print(f"  - {func}")
    
    # Affected tests
    if report.affected_tests:
        print("\n✓ AFFECTED TESTS:")
        for test in report.affected_tests:
            confidence_str = f" [{test.confidence:.0%}]" if args.show_scores else ""
            print(f"  • {test.test_file}{confidence_str}")
            if args.verbose:
                print(f"    {test.reason}")
                for func in test.affected_functions:
                    print(f"      ↳ {func}")
    
    # Unaffected (summary)
    if report.unaffected_tests and args.verbose:
        print(f"\n✗ Unaffected Tests: {len(report.unaffected_tests)} tests")
        if len(report.unaffected_tests) <= 10:
            for test in report.unaffected_tests[:10]:
                print(f"  - {test}")
        else:
            print(f"  (showing first 10 of {len(report.unaffected_tests)})")
    
    print("\n" + "=" * 70)


def run_affected_tests(report, args):
    """Run only the affected tests."""
    if not report.affected_tests:
        print("No tests affected by changes.")
        return
    
    print(f"\nRunning {len(report.affected_tests)} affected tests...\n")
    
    test_files = [t.test_file for t in report.affected_tests]
    
    # Simple serial execution
    failed_tests = []
    for test_file in test_files:
        print(f"Running: {test_file}")
        result = subprocess.run(
            ['bash', test_file],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            failed_tests.append(test_file)
            print(f"  ❌ FAILED")
        else:
            print(f"  ✓ PASSED")
    
    # Summary
    print(f"\n\nResults: {len(test_files) - len(failed_tests)}/{len(test_files)} passed")
    if failed_tests:
        print(f"\nFailed tests:")
        for test in failed_tests:
            print(f"  - {test}")
        sys.exit(1)


def run_all_tests(args):
    """Run all tests."""
    print("Running all tests...\n")
    result = subprocess.run(
        ['bash', 'tests/run_tests.sh'],
        cwd=args.working_dir
    )
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
