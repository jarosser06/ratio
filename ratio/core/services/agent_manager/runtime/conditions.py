"""
ConditionEvaluator

This module provides a class for evaluating conditions based on a reference object.
"""
import logging

from typing import Any, Dict, List, Union

from ratio.core.services.agent_manager.runtime.reference import Reference


class ConditionEvaluator:
    def __init__(self, reference: Reference, token: str):
        """
        Initialize the ConditionEvaluator with a reference and token.

        Keyword arguments:
        reference -- A Reference object to resolve parameters
        token -- A token to be used for resolving parameters
        """
        self.reference = reference

        self.token = token

    def evaluate(self, conditions: Union[List, Dict]) -> bool:
        """
        Main entry point for condition evaluation

        Keyword arguments:
        conditions -- A list of conditions or a condition group
        """
        if isinstance(conditions, list):
            # Simple list of conditions (backward compatibility)
            return self._evaluate_condition_list(conditions, "AND")

        if isinstance(conditions, dict):
            # Structured condition object
            return self._evaluate_condition_group(conditions)

        return True  # No conditions

    def _evaluate_condition_group(self, group: Dict) -> bool:
        """
        Evaluate a condition group (with potential nested groups)

        Keyword arguments:
        group -- A dictionary representing a condition group
        """
        logic = group.get("logic", "AND")

        # Evaluate direct conditions in this group
        direct_conditions = group.get("conditions", [])

        direct_results = []

        for condition in direct_conditions:
            result = self._evaluate_single_condition(condition)

            direct_results.append(result)

        # Evaluate nested groups
        nested_groups = group.get("groups", [])

        nested_results = []

        for nested_group in nested_groups:
            result = self._evaluate_condition_group(nested_group)

            nested_results.append(result)

        # Combine all results
        all_results = direct_results + nested_results

        if not all_results:
            return True  # Empty group passes

        if logic == "AND":
            return all(all_results)

        else:  # OR
            return any(all_results)

    def _evaluate_condition_list(self, conditions: List, logic: str = "AND") -> bool:
        """
        Evaluate a simple list of conditions

        Keyword arguments:
        conditions -- A list of conditions
        logic -- The logic to apply (AND/OR)
        """
        if not conditions:
            return True

        results = []

        for condition in conditions:
            result = self._evaluate_single_condition(condition)

            results.append(result)

        if logic == "AND":
            return all(results)

        else:  # OR
            return any(results)

    def _evaluate_single_condition(self, condition: Dict) -> bool:
        """
        Evaluate a single condition

        Keyword arguments:
        condition -- A dictionary representing a single condition
        """
        try:
            param_value = condition["param"]

            if condition["param"].startswith("REF:"):
                logging.debug(f"Resolving reference for {param_value}")

                # Special case for ratio parameters
                param_value = self.reference.resolve(
                    reference_string=condition["param"], 
                    token=self.token
                )

                logging.debug(f"Resolved value: {param_value}")

            operator = condition["operator"]

            expected_value = condition.get("value")

            return self._apply_operator(param_value, operator, expected_value)

        except Exception as e:
            logging.warning(f"Condition evaluation failed: {e}")

            return False

    def _apply_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        """
        Apply the comparison operator

        Keyword arguments:
        actual -- The actual value to compare
        operator -- The operator to apply
        expected -- The expected value to compare against
        """
        logging.debug(f"Applying operator: {operator} on {actual} and {expected}")

        if operator == "equals":
            return actual == expected

        elif operator == "not_equals":
            return actual != expected

        elif operator == "exists":
            return actual is not None

        elif operator == "not_exists":
            return actual is None

        elif operator == "greater_than":
            return actual > expected

        elif operator == "less_than":
            return actual < expected

        elif operator == "greater_than_or_equal":
            return actual >= expected

        elif operator == "less_than_or_equal":
            return actual <= expected

        elif operator == "contains":
            return expected in actual

        elif operator == "not_contains":
            return expected not in actual

        elif operator == "in":
            return actual in expected

        elif operator == "not_in":
            return actual not in expected

        elif operator == "starts_with":
            return str(actual).startswith(str(expected))

        elif operator == "ends_with":
            return str(actual).endswith(str(expected))

        else:
            raise ValueError(f"Unknown operator: {operator}")