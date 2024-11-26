#!/usr/bin/env python3

"""
Functions related to Vargha and Delaneys A^{hat}_{12}() test to measure effect size.
* a12(baseline_data, tweak_data) -> effect size
* effect_size_categorization(effect_size) -> string 'interpreting' effect size
"""

from typing import List

def a12(baseline: List[int], tweak: List[int]) -> float:
    """
    Calculate A12 ("A12-hat") effect size as specified by Vargha and Delaney [1]
    Code is adapted from Tim Menzies Python implementation [2]

    To this end, expects two lists of mean/median coverage values, one for the
    baseline and one for the tweak (your hopefully better tool).
    Calculates a single floating point value between 0 and 1 to be interpreted
    as follows:
    effect_size == 0.5: both tools are equal
    effect_size > 0.5: positive effect size
    effect_size < 0.5: negative effect size

    Further categorization in small, medium, and large effect size is possible
    (based on values by [1]):
    effect_size > 0.56: small positive effect size
    effect_size > 0.64: medium positive effect size
    effect_size > 0.71: large positive effect size

    Parameters
    ----------
    baseline : List[int]
                list of median coverage values for baseline tool (e.g., AFL++)
    tweak : List[int]
                list of median coverage values for your tool

    Returns
    -------
    effect_size : float
                    A12 effect size (0 <= effect_size <= 1.0)

    References
    ----------
    [1] András Vargha and Harold D. Delaney. 2000. A Critique and Improvement of
    the CL Common Language Effect Size Statistics of McGraw and Wong. Journal of
    Educational and Behavioral Statistics 25, 2 (2000).
    [2] Tim Menzies. https://gist.github.com/timm/5630491
    """
    assert len(baseline) == len(tweak), f"len(baseline)={len(baseline)} != len(tweak)={len(tweak)}"
    more: int = 0
    same: int = 0
    for x in tweak:
        for y in baseline:
            if x == y:
                same += 1
            elif x > y:
                more += 1
    return (more + 0.5 * same)  / (len(baseline) * len(tweak))


def effect_size_categorization(effect_size: float) -> str:
    """
    Categorize effect size according to the boundaries suggest by Vargha and Delaney [1].

    A negative or positive effect size can be discerned (expressed as "+" or "-")
    effect_size == 0.5: both tools are equal
    effect_size > 0.5: positive effect size
    effect_size < 0.5: negative effect size

    Further categorization in small, medium, and large effect size is possible
    (based on values by [1]):
    effect_size > 0.56: small positive effect size
    effect_size > 0.64: medium positive effect size
    effect_size > 0.71: large positive effect size

    Parameters
    ----------
    effect_size : float
                Effect size (must be 0 <= effect_siez <= 1)

    Returns
    -------
    category : str
                A string describing the effect size (categorized in Large, Medium, Small)

    References
    ----------
    [1] András Vargha and Harold D. Delaney. 2000. A Critique and Improvement of
    the CL Common Language Effect Size Statistics of McGraw and Wong. Journal of
    Educational and Behavioral Statistics 25, 2 (2000).
    """
    if effect_size > 0.71:
        return "+L"
    elif effect_size > 0.64:
        return "+M"
    elif effect_size > 0.56:
        return "+S"
    elif effect_size > 0.50:
        return "  "
    elif effect_size == 0.50:
        return "  "
    elif effect_size < 0.29:
        return "-L"
    elif effect_size < 0.36:
        return "-M"
    elif effect_size < 0.44:
        return "-S"
    elif effect_size < 0.50:
        return "  "
    raise ValueError(f"effect size must be 0 <= effect_size <= 1; but is {effect_size}")


def effect_size_latex_table_field(effect_size: float) -> str:
    category = effect_size_categorization(effect_size)
    return f"{category}({round(effect_size, 2):.2f})"


if __name__ == "__main__":
    # baseline = [30165, 30522, 31025, 31275, 31879]
    # tweak = [34303, 34592, 35453, 36207, 37394]

    baseline = [11377, 11707, 11731, 11899, 12178]
    tweak = [11703, 11791, 12030, 12039, 12135]

    effect_size = a12(baseline, tweak)
    print(f"{baseline=}")
    print(f"{tweak=}")
    print(f"{effect_size=}")
