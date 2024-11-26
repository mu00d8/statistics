#!/usr/bin/env python3

from argparse import Namespace
from statistics import mean, median
from rpy2.robjects.packages import STAP # type: ignore
from rpy2.robjects.vectors import FloatVector, ListVector # type: ignore
from typing import Any, Dict, List, Optional, Tuple
from utils import compare_against_best_competitor, compare_pairwise, effect_size_latex_table_field, a12


R_Script: Optional[str] = None


def load_r_script() -> None:
    global R_Script
    with open("statistics.R", "r", encoding="utf-8") as f:
        R_Script = f.read()


def parse_posthoc_results(decisions_posthoc: Any, fuzzers: List[str]) -> None:
    assert len(decisions_posthoc) == 4
    posthoc_decision = decisions_posthoc[0]
    for dec in decisions_posthoc[0]:
        assert dec in (1.0, 1, 0.0, 0), f"Unexpected decision: {dec}"
    posthoc_test_statistics = decisions_posthoc[1]
    sample_1_idx = decisions_posthoc[2]
    sample_2_idx = decisions_posthoc[3]
    for i in range(len(decisions_posthoc[0])):
        # indices are floats -- sanity check they are indeed indices
        s1_idx = int(sample_1_idx[i])
        assert s1_idx == sample_1_idx[i]
        s2_idx = int(sample_2_idx[i])
        assert s2_idx == sample_2_idx[i]

        # decrement indices by 1 as R starts them with 1 rather than 0
        sample1 = fuzzers[s1_idx - 1]
        sample2 = fuzzers[s2_idx - 1]
        print(
            f"{sample1:16} vs {sample2:16}: {str(bool(posthoc_decision[i])):5}" \
            f" (statistics: {round(posthoc_test_statistics[i], 2)})"
        )


def test_twoway(data: Dict[str, List[int]], args: Namespace) -> bool:
    assert args.tweak in data, f"Did not found new fuzzer '{args.tweak}' in data"
    assert R_Script is not None
    r_stat = STAP(R_Script, "stat") # type: ignore
    f1: FloatVector = FloatVector(data[args.tweak]) # type: ignore
    other_ks = set(data.keys())
    other_ks.remove(args.tweak)
    other_k = other_ks.pop()
    f2: FloatVector = FloatVector(data[other_k]) # type: ignore
    print(f"[i] Two sample comparison: {args.tweak} vs {other_k}")
    print(f"[d] {args.tweak:16} -> {sorted(data[args.tweak])}")
    print(f"[d] {other_k:16} -> {sorted(data[other_k])}")
    result: List[float] = r_stat.dec_twosamplecomparison(f1=f1, f2=f2, alpha=0.05, B=999) # type: ignore
    assert len(result) == 3, f"Unexpected response vector: {result}" # type: ignore
    test_statistics, critical_value, test_decision = result[:3] # type: ignore
    dec = True if test_decision == 1.0 else False
    print(f"[i] {test_statistics=} {critical_value=} significant? {dec}")
    if not args.no_effect_size:
        effect_size = a12(baseline=data[other_k], tweak=data[args.tweak])
        effect_size_field = effect_size_latex_table_field(effect_size)
        print(f"[i] Effect size: {effect_size_field}")
    return dec


def perc_difference(data: Dict[str, List[int]], primary: str, baseline: Optional[str], args: Namespace) \
            -> Optional[Tuple[float, float]]:
    """
    Calculate and return percentage of improvement and factor between primary and baseline
    (or best competitor if baseline is None)

    Uses median (and, for finding the best competitor, where two can have the same median, we use the mean as secondary
    criterion). This can be inverted by setting args.use_mean: Then, we use the mean (and if needed median as secondary
    criterion).
    """
    # difference of `primary` to the best competitor (fuzzer with highest median coverage)
    # if two competitors have same median, use higher average
    if not primary in data:
        print(f"[!] Primary fuzzer {primary} not found in data")
        return None
    # if desired by the user, we can use the mean for primary comparison (and the median if both are equal)
    if args.use_mean:
        fmp = mean
        fms = median
    else:
        fmp = median
        fms = mean
    if not baseline:
        print("[i] No baseline specified, using best competitor")
        best_competitor: Tuple[str, List[int]] = ("NONE", [0] * args.expected_runs)
        mbc = 0
        for k, v in data.items():
            if k == primary:
                continue
            mv = fmp(v)
            mbc = fmp(best_competitor[1])
            if mv > mbc:
                best_competitor = (k, v)
            elif mv == mbc:
                if fms(v) > fms(best_competitor[1]):
                    best_competitor = (k, v)
        mbc = fms(best_competitor[1])
    else:
        if not baseline in data:
            print(f"[!] Baseline fuzzer {baseline} not found in data")
            return None
        best_competitor = (baseline, data[baseline])
        mbc = median(data[baseline])
    if args.debug:
        print(f"[d] Best competitor: {best_competitor[0]} with median {mbc}")
    mpr = fmp(data[primary])
    diff_m = mpr - mbc
    p = round(100 * diff_m / mbc, 2)
    print(f"[i] {fmp.__name__} {args.tweak}={mpr} <-> {mbc} ({best_competitor[0]})")
    print(f"[i] Difference of {fmp.__name__}s: {diff_m} {p}% more coverage ({round(mpr / mbc, 2)} times better)")
    # returns coverage improvement and factor
    return (p, mpr / mbc)


def test_best_competitor(data: Dict[str, List[int]], primary: str, args: Namespace) \
        -> Optional[Tuple[str, List[int], bool]]:
    # twoway test `primary` against the best competitor (fuzzer with highest median coverage)
    # if two competitors have same median, use higher average
    if not primary in data:
        print(f"[!] Primary fuzzer {primary} not found in data")
        return None
    best_competitor: Tuple[str, List[int]] = ("NONE", [0] * args.expected_runs)
    mbc = 0
    for k, v in data.items():
        if k == primary:
            continue
        mv = median(v)
        mbc = median(best_competitor[1])
        if mv > mbc:
            best_competitor = (k, v)
        elif mv == mbc:
            if mean(v) > mean(best_competitor[1]):
                best_competitor = (k, v)
    print(f"[i] Best competitor: {best_competitor[0]} with median {mbc}")

    decision = test_twoway({primary : data[primary], best_competitor[0] : best_competitor[1]}, args)

    return (best_competitor[0], best_competitor[1], decision)


def test_data(data: Dict[str, List[int]], args: Namespace) -> None:
    assert R_Script is not None
    r_stat = STAP(R_Script, "stat") # type: ignore
    print("#"*10)
    print(f"R magic! Found {len(data)} fuzzers..")
    if len(data.keys()) == 2:
        test_twoway(data, args)
    elif len(data.keys()) > 2:
        fuzzers: List[str] = []
        fs: List[FloatVector] = [] # type: ignore
        for fuzzer, fuzzer_data in data.items():
            print(f"{fuzzer=:16} -> {fuzzer_data}")
            if args.allow_missing_runs:
                if len(fuzzer_data) < args.expected_runs:
                    print(f"[!] {fuzzer}: Expected {args.expected_runs}, found {len(fuzzer_data)}")
                    continue
            else:
                assert len(fuzzer_data) == args.expected_runs, \
                        f"{fuzzer}: Expected {args.expected_runs}, found {len(fuzzer_data)}"
            vec: FloatVector = FloatVector(fuzzer_data) # type: ignore
            if len(set(fuzzer_data)) < 3:
                print(f"[!] {fuzzer}: data is essentially constant. Skipping this fuzzer")
                continue
            fuzzers.append(fuzzer)
            fs.append((fuzzer, vec)) # type: ignore
        if len(fs) < 2: # type: ignore
            print("[!] Not enough groups to run a test. Skipping this target")
            return
        print()
        print("Running dec_anova")
        fs_vec = ListVector(fs) # type: ignore
        result = r_stat.dec_anova(fs_vec, alpha=0.05, B=999) # type: ignore
        assert len(result) == 5, f"Unexpected response vector: {result}" # type: ignore
        decision_anova_vec, test_statistics_anova_vec, critvals, decisions_posthoc, decisions_posthoc_mean = result[:5] # type: ignore
        
        # parse anova decision
        assert len(decision_anova_vec) == 1, f"Decision anova vector: expected len=1 found {len(decision_anova_vec)}" # type: ignore
        decision_anova = decision_anova_vec[0] # type: ignore
        
        # parse anova test statistics
        assert len(test_statistics_anova_vec) == 1 # type: ignore
        test_statistics_anova = test_statistics_anova_vec[0] # type: ignore
        
        # parse critvals list
        critvals = list(critvals) # type: ignore
        # critvals[0] = crit val of anova
        # critvals[1] = crit val of posthoc
        # critvals[2] = crit val of posthoc_means
        
        # parse posthoc
        # decision_posthoc(_means) has 4 columns: TEST_DECISION | TEST_STATISTICS | sample_1_idx | sample_2_idx
        print("Posthoc results")
        parse_posthoc_results(decisions_posthoc, fuzzers)
        print()

        print("Posthoc MEAN results")
        parse_posthoc_results(decisions_posthoc_mean, fuzzers)

        print(f"{decision_anova=}, {test_statistics_anova=}, {critvals=}")
        if args.debug:
            print("\n")
            print("-"*10)
            print(result) # type: ignore
            print("-"*10)
    else:
        print(f"[!] Not enough data to compare fuzzers: keys={list(data.keys())}")
    print("\n"*3)


def gen_paper_table(data: Dict[str, Dict[str, List[int]]], args: Namespace) -> None:
    table: List[str] = []
    for target, target_data in data.items():
        if args.eval_targets and target not in args.eval_targets:
            continue
        print(f"[i] {target=}")
        if not args.tweak in target_data:
            print(f"[!] {target}: Tweak={args.tweak} not in target_data")
            continue
        if len(target_data) < 2:
            print(f"[!] {target}: Data for less than 2 fuzzers ({list(target_data.keys())})")
            continue
        res = test_best_competitor(target_data, args.tweak, args)
        if res is None:
            print(f"[!] Skipping {target}")
            continue
        bc, bc_cov, dec = res
        assert dec is not None, f"{target}: {bc=} {bc_cov=} {dec=}"
        if len(bc_cov) != len(target_data[args.tweak]):
            print(f"[!] num_runs[best_comp]={len(bc_cov)} <-> num_runs[tweak]={len(target_data[args.tweak])}")
            continue
        eff_sz = a12(bc_cov, target_data[args.tweak])
        eff_sz_field = effect_size_latex_table_field(eff_sz)
        if dec:
            eff_sz_field = r"\textbf{" + eff_sz_field + r"}"
        else:
            eff_sz_field = " " * 8 + eff_sz_field + " "
        latex_target = target.replace("_", r"\_")
        row = f"{latex_target:34} & \\{bc:10} & {eff_sz_field:8} \\\\"
        table.append(row)
    print("\n"*3)
    print("\n".join(table))


# traditional MWU test
def traditional_MWU_test(data: Dict[str, List[int]], args: Namespace) -> None:
    if args.only_best_competitor:
        compare_against_best_competitor(args.tweak, data)
    else:
        compare_pairwise(data)


def main(args: Namespace, data: Dict[str, Dict[str, List[int]]]) -> None:
    load_r_script()

    if args.subcommand == "gen-table":
        return gen_paper_table(data, args)

    cov_percs: List[float] = []
    factors: List[float] = [] # only used by subcommand "improvement"
    for target, target_data in data.items():
        if args.eval_targets and target not in args.eval_targets:
            continue
        # skip incomplete targets where we have only data for 1 fuzzer
        if len(target_data) == 1:
            print(f"[!] {target}: Skipping this target as we only have data for 1 fuzzer\n")
            continue
        print(f"# {target}")
        for k, v in target_data.items():
            if len(v) != args.expected_runs:
                print(f"[!] {target}: {k} only has {len(v)} runs (expected {args.expected_runs})")
        if args.subcommand == "improvement":
            res = perc_difference(target_data, args.tweak, args.baseline, args)
            if res:
                cov_perc, fac = res
                factors.append(fac)
                cov_percs.append(cov_perc)
        elif args.subcommand == "baseline":
            if not args.baseline in target_data:
                print(f"[!] Baseline {args.baseline} has no data for target {target}")
                print()
                continue
            baseline_data = {
                str(args.baseline) : target_data[args.baseline],
                str(args.tweak) : target_data[args.tweak],
            }
            test_twoway(baseline_data, args)
        elif args.subcommand == "traditional":
            traditional_MWU_test(target_data, args)
        elif args.subcommand == "best-competitor":
            test_best_competitor(target_data, args.tweak, args)
        elif args.subcommand == "full-comparison":
            test_data(target_data, args)
        else:
            raise ValueError(f"No subcommand specified: {args.subcommand}")
        print()
    if factors:
        print(f"[i] Raw factors: {factors}")
        print(f"[i] Average improvement: {mean(factors)} (median: {median(factors)})")
        print(f"[i] Worst improvement: {min(factors)}")
        print(f"[i] Best improvement: {max(factors)}")
        print()
    if cov_percs:
        print(f"[i] Raw percentages: {cov_percs}")
        print(f"[i] Average improvement: {mean(cov_percs)}% (median: {median(cov_percs)}%)")
        print(f"[i] Worst improvement: {min(cov_percs)}%")
        print(f"[i] Best improvement: {max(cov_percs)}%")
