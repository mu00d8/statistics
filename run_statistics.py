#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import Optional

from statistical_tests import main

R_Script: Optional[str] = None

# TODO: need to set the names of the baseline and your fuzzer (must match fuzzer keys of data dict)
BASELINE = "aflpp"
TWEAK = "new_fuzzer"

# TODO: parse your data or hardcode it here
# Expected format:
# {
#   "TARGET" : {
#       "FUZZER 1" : [final_coverage_of_run_1, ..., final_coverage_of_run_10],
#       "FUZZER 2" : [final_coverage_of_run_1, ..., final_coverage_of_run_10],
#   }
# }

# Examplary data
DATA = {
    "Example 1": {
        "aflpp": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009],
        "new_fuzzer": [1111] * 10,
        "test": [1234] * 10,
    },
    "Example 2" : {
        "aflpp": [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009],
        "new_fuzzer": [999] * 10,
        "test": [1234] * 10,
    }
}

if __name__ == "__main__":
    parser = ArgumentParser(description="Run statistics for your shiny new fuzzer")
    # subcommands / mode to run
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand/mode to run", required=True)
    subparsers.add_parser("gen-table", help="Generate LaTeX table body for paper")
    subparsers.add_parser("best-competitor", help="Two-way test against best competitor")
    subparsers.add_parser("improvement", help="Calculate average improvement and improvement per target")
    sp = subparsers.add_parser("traditional", help="Traditional MWU instead of bootstrap-based test")
    sp.add_argument("--only-best-competitor", action="store_true", default=False, help="Compare only against the best competitor")
    subparsers.add_parser("baseline", help="Compare tweak (new fuzzer) to baseline")
    subparsers.add_parser("full-comparison", help="Run a full ANOVA+posthoc of all data")

    # global options
    parser.add_argument("--baseline", default=BASELINE, help="Baseline fuzzer")
    parser.add_argument("--tweak", default=TWEAK, help="New fuzzer ('tweak' of the baseline)")
    parser.add_argument("--expected-runtime", type=str, default="86400s", help="Filter for specific runtime")
    parser.add_argument("--expected-runs", type=int, default=10, help="Number of runs we expect")
    parser.add_argument("--use-mean", action="store_true", default=False, help="Use mean instead of median")
    parser.add_argument("--no-effect-size", action="store_true", default=False, help="Do not calculate effect size")
    parser.add_argument("--allow-missing-runs", action="store_true", default=False,
                        help="Allow missing runs (fuzzer with missing runs are just ignored)")
    parser.add_argument("--eval-targets", nargs="+", default=None,
                        help="Only print specified evaluation targets")

    # debug options
    parser.add_argument("--debug", action="store_true", default=False, help="Debug output")
    
    main(parser.parse_args(), DATA)
