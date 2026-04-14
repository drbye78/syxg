#!/usr/bin/env python3
"""
Test Runner for XG Synthesizer Test Suite

Runs all tests or specific test categories with various options.
"""

import sys
import argparse
import subprocess


def run_tests(args):
    """Run pytest with specified arguments."""
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add coverage if requested
    if args.coverage:
        cmd.extend(["--cov=synth", "--cov-report=xml", "--cov-report=term"])

    # Add specific test markers
    if args.unit:
        cmd.extend(["-m", "unit"])
    elif args.integration:
        cmd.extend(["-m", "integration"])
    elif args.system:
        cmd.extend(["-m", "system"])
    elif args.performance:
        cmd.extend(["-m", "performance"])

    # Add specific test file
    if args.test_file:
        cmd.append(args.test_file)
    else:
        cmd.append("tests/")

    # Add parallel execution
    if args.parallel:
        cmd.extend(["-n", "auto"])

    # Add slow test handling
    if not args.include_slow:
        cmd.extend(["-m", "not slow"])

    # Add SF2 file requirement
    if args.requires_sf2:
        cmd.extend(["-m", "requires_sf2"])

    # Run tests
    print(f"Running tests with command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd="/mnt/c/work/guga/syxg")
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run XG Synthesizer Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tests
  python tests/run_tests.py

  # Run only unit tests
  python tests/run_tests.py --unit

  # Run with coverage
  python tests/run_tests.py --coverage

  # Run specific test file
  python tests/run_tests.py --test-file tests/test_sf2_zone_selection.py

  # Run integration tests with verbose output
  python tests/run_tests.py --integration --verbose

  # Run performance tests
  python tests/run_tests.py --performance

  # Run tests in parallel
  python tests/run_tests.py --parallel
        """,
    )

    parser.add_argument(
        "--unit", action="store_true", help="Run unit tests only"
    )
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--system", action="store_true", help="Run system tests only"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose output"
    )
    parser.add_argument(
        "--test-file", type=str, help="Run specific test file"
    )
    parser.add_argument(
        "--parallel", "-n", action="store_true", help="Run tests in parallel"
    )
    parser.add_argument(
        "--include-slow", action="store_true", help="Include slow tests"
    )
    parser.add_argument(
        "--requires-sf2", action="store_true", help="Run only tests requiring SF2 files"
    )

    args = parser.parse_args()

    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())