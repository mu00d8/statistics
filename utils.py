#!/usr/bin/env python3

"""
Provide some convenience methods for statistical evaluation of fuzzing runs
"""

import itertools
import sys
from statistics import mean, median
from scipy.stats import mannwhitneyu # type: ignore
from typing import List, Dict, Tuple
from a12 import a12, effect_size_latex_table_field


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def find_best_competitor(tweak: str, fuzzer_to_bbs: Dict[str, List[int]], method: str = 'median') -> List[str]:
    """
    Find best competitor of tweak using a specific method (by default the median)

    Parameters
    ----------
    tweak : str
            name of your fuzzer (the "tweak")
    fuzzer_to_bbs: Dict[str, List[int]]
            dict that maps fuzzer names to a list, where each element represents the number of total basic blocks
            found by one run (i.e., len(list) == num_runs)
    methods: str = 'median'
            Methods to use to identify the best competitor (supports 'mean' and 'median', the latter being the default) 

    Returns
    -------
    best_competitor : List[str]
                name of the best competitor(s) -- multiple may exist if they are equal under 'method'
    """
    fn = median
    if method == "mean":
        fn = mean
    ratings: Dict[str, float] = {}
    for fuzzer, bbs in fuzzer_to_bbs.items():
        if fuzzer == tweak:
            continue
        ratings[fuzzer] = fn(bbs)
    max_val = max([v for v in ratings.values()])
    best = [f for f, v in ratings.items() if v == max_val]
    return best


def mann_whitney_u(baseline: List[int], tweak: List[int], unsafe: bool = False, quiet: bool = False) -> Tuple[float, float]:
    if not unsafe:
        assert not contains_ties(baseline+tweak), "'exact' Mann-Whitney-U test may not contain ties in data"
    elif not quiet:
        validate_datasets(baseline, tweak, "baseline", "tweak")
    mwu_result = mannwhitneyu(
        x=baseline,
        y=tweak,
        alternative="two-sided",
        method="exact"
    )
    stat: float = mwu_result[0] # type: ignore
    p_value: float = mwu_result[1] # type: ignore
    return stat, p_value # type: ignore


def compare_against_baseline(fuzzer_data: Dict[str, List[int]], baseline: str) -> None:
    assert baseline in fuzzer_data, f"Baseline {baseline} not in data: {fuzzer_data}"
    for fuzzer, values in fuzzer_data.items():
        if fuzzer == baseline:
            continue
        effect_size = a12(baseline=fuzzer_data[baseline], tweak=values)
        effect_size_field = effect_size_latex_table_field(effect_size)
        _, p_val = mann_whitney_u(baseline=fuzzer_data[baseline], tweak=values, unsafe=True)
        print(f"{fuzzer:32} (tweak) vs {baseline:16} (baseline): p_val={p_val:.4f} (< 0.05? {str(p_val < 0.05):5}), {effect_size_field}")


def compare_pairwise(fuzzer_data: Dict[str, List[int]]) -> None:
    for tw_tup, bl_tup in itertools.permutations(fuzzer_data.items(), 2):
        effect_size = a12(baseline=bl_tup[1], tweak=tw_tup[1])
        effect_size_field = effect_size_latex_table_field(effect_size)
        _, p_val = mann_whitney_u(baseline=bl_tup[1], tweak=tw_tup[1], unsafe=True)
        print(f"{tw_tup[0]:10} (tweak) vs {bl_tup[0]:10} (baseline): p_val={p_val:.4f} (< 0.05? {str(p_val < 0.05):5}), {effect_size_field}")
        # best_competitor_data.append((bl_tup, p_val, effect_size))
    #return best_competitor_data


def compare_against_best_competitor(tweak: str, fuzzer_data: Dict[str, List[int]]) -> List[Tuple[str, float, float]]:
    best_competitor = find_best_competitor(tweak, fuzzer_data)
    if len(best_competitor) != 1:
        print(f"[i] Found {len(best_competitor)} best competitors: {best_competitor}")
    best_competitor_data: List[Tuple[str, float, float]] = []
    for comp in best_competitor:
        effect_size = a12(baseline=fuzzer_data[comp], tweak=fuzzer_data[tweak])
        effect_size_field = effect_size_latex_table_field(effect_size)
        _, p_val = mann_whitney_u(baseline=fuzzer_data[comp], tweak=fuzzer_data[tweak], unsafe=True)
        print(f"{comp}: p_val={p_val:.4f} (< 0.05? {p_val < 0.05}), {effect_size_field}")
        best_competitor_data.append((comp, p_val, effect_size))
    return best_competitor_data


def contains_zero(data: List[int]) -> bool:
    """
    Check whether the data contains zero as value
    """
    if 0 in data:
        return True
    return False


def contains_ties(data: List[int]) -> bool:
    """
    Check whether data contains ties, i.e., one (or more) elements are contained more than once
    """
    if len(set(data)) != len(data):
        return True
    return False


def num_ties(data: List[int]) -> int:
    return len(data) - len(set(data))


def contains_overlaps(data_a: List[int], data_b: List[int]) -> bool:
    return len(set(data_a).intersection(set(data_b))) > 0


def validate_data(data: List[int], label: str) -> bool:
    """
    Check and warn if data contains zeroes or ties
    """
    is_valid = True
    if contains_zero(data):
        print(f"[!] Data of {label} contains 0 ({data.count(0)} times)")
        is_valid = False
    if contains_ties(data):
        for e in set(data):
            if data.count(e) > 1:
                print(f"[!] Data of {label} contains {e} {data.count(e)} times")
                is_valid = False
    return is_valid


def validate_datasets(data_a: List[int], data_b: List[int], label_a: str, label_b: str) -> bool:
    is_valid = True
    if contains_ties(data_a):
        eprint(f"[!] {label_a} contains {num_ties(data_a)} ties: {sorted(data_a)}")
        is_valid = False
    if contains_ties(data_b):
        eprint(f"[!] {label_b} contains {num_ties(data_b)} ties: {sorted(data_b)}")
        is_valid = False
    if contains_ties(data_a + data_b):
        eprint(f"[!] {label_a}+{label_b} contains {num_ties(data_a + data_b)} ties: {sorted(data_a + data_b)}")
        is_valid = False
    return is_valid


if __name__ == "__main__":
    fuzzer_to_bbs = {
        "tweak"    : [12001, 10345, 11453, 11990, 12040],
        "fuzzer-1" : [11377, 11707, 11731, 11899, 12178],
        "fuzzer-2" : [11703, 11791, 12030, 12039, 12135],
        "fuzzer-3" : [12340, 10000, 15000,  9000, 11132]
    }
    print(find_best_competitor("tweak", fuzzer_to_bbs))
