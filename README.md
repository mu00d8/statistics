# Scripts for a statistical evaluation of fuzzing campaigns

Collection of scripts for running a statistical evaluation of fuzzers (using bootstrap-based methods, see https://github.com/fuzz-evaluator/statistics). This may need R and the dependencies in requirements.txt.

To use this, you either need to write parsing logic extracting the final coverage data and put that in run_statistics.py, or you just hardcode these values there. 
Then run one of the subcommands, like `run_statistics.py gen-table` to generate the body of a LaTeX table.
