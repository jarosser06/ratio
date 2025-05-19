"""
Quick test script for the ConditionEvaluator class
"""

import logging
from typing import Any, Dict, List, Union
from unittest.mock import Mock

# Set up logging
logging.basicConfig(level=logging.INFO)

class MockReference:
    """Mock reference resolver for testing"""
    def __init__(self):
        self.values = {
            "REF:user.active": True,
            "REF:user.level": "admin",
            "REF:user.permissions": ["read", "write", "execute"],
            "REF:data.count": 25,
            "REF:data.status": "ready",
            "REF:quota.remaining": 100,
            "REF:environment.type": "production",
            "REF:override.enabled": False,
            "REF:arguments.force": True,
            "REF:previous.success": True,
            "REF:score.value": 85.5,
        }
    
    def resolve(self, reference_string: str, token: str = None) -> Any:
        if reference_string in self.values:
            return self.values[reference_string]
        raise ValueError(f"Unknown reference: {reference_string}")

class ConditionEvaluator:
    def __init__(self, reference, token: str = "mock_token"):
        self.reference = reference
        self.token = token
    
    def evaluate(self, conditions: Union[List, Dict]) -> bool:
        """Main entry point for condition evaluation"""
        if isinstance(conditions, list):
            # Simple list of conditions (backward compatibility)
            return self._evaluate_condition_list(conditions, "AND")
        
        if isinstance(conditions, dict):
            # Structured condition object
            return self._evaluate_condition_group(conditions)
        
        return True  # No conditions
    
    def _evaluate_condition_group(self, group: Dict) -> bool:
        """Evaluate a condition group (with potential nested groups)"""
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
        """Evaluate a simple list of conditions"""
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
        """Evaluate a single condition"""
        try:
            param_value = condition["param"]
            if condition["param"].startswith("REF:"):
                # Special case for ratio parameters
                param_value = self.reference.resolve(
                    reference_string=condition["param"], 
                    token=self.token
                )
            
            operator = condition["operator"]
            expected_value = condition.get("value")
            
            return self._apply_operator(param_value, operator, expected_value)
        
        except Exception as e:
            logging.warning(f"Condition evaluation failed: {e}")
            return False
    
    def _apply_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        """Apply the comparison operator"""
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

def run_tests():
    """Run test cases for the ConditionEvaluator"""
    
    # Set up mock reference and evaluator
    mock_ref = MockReference()
    evaluator = ConditionEvaluator(mock_ref)
    
    # Test cases
    test_cases = [
        # Simple condition list (backward compatibility)
        {
            "name": "Simple list - all true",
            "conditions": [
                {"param": "REF:user.active", "operator": "equals", "value": True},
                {"param": "REF:data.count", "operator": "greater_than", "value": 10}
            ],
            "expected": True
        },
        
        # Static value conditions (your improvement)
        {
            "name": "Static value condition",
            "conditions": [
                {"param": "static_value", "operator": "equals", "value": "static_value"},
                {"param": "REF:user.active", "operator": "equals", "value": True}
            ],
            "expected": True
        },
        
        # Simple group with AND logic
        {
            "name": "Simple AND group",
            "conditions": {
                "logic": "AND",
                "conditions": [
                    {"param": "REF:user.active", "operator": "equals", "value": True},
                    {"param": "REF:user.level", "operator": "equals", "value": "admin"}
                ]
            },
            "expected": True
        },
        
        # Simple group with OR logic
        {
            "name": "Simple OR group",
            "conditions": {
                "logic": "OR",
                "conditions": [
                    {"param": "REF:user.level", "operator": "equals", "value": "user"},  # False
                    {"param": "REF:user.active", "operator": "equals", "value": True}   # True
                ]
            },
            "expected": True
        },
        
        # Complex nested groups
        {
            "name": "Complex nested groups",
            "conditions": {
                "logic": "AND",
                "groups": [
                    {
                        "logic": "OR",
                        "conditions": [
                            {"param": "REF:data.status", "operator": "equals", "value": "ready"},
                            {"param": "REF:arguments.force", "operator": "equals", "value": True}
                        ]
                    },
                    {
                        "logic": "AND",
                        "conditions": [
                            {"param": "REF:user.permissions", "operator": "contains", "value": "execute"},
                            {"param": "REF:quota.remaining", "operator": "greater_than", "value": 0}
                        ]
                    }
                ]
            },
            "expected": True
        },
        
        # Test with various operators
        {
            "name": "Various operators",
            "conditions": {
                "logic": "AND",
                "conditions": [
                    {"param": "REF:user.level", "operator": "in", "value": ["admin", "superuser"]},
                    {"param": "REF:user.permissions", "operator": "contains", "value": "write"},
                    {"param": "REF:score.value", "operator": "greater_than_or_equal", "value": 80.0},
                    {"param": "REF:environment.type", "operator": "starts_with", "value": "prod"}
                ]
            },
            "expected": True
        },
        
        # Test failure case
        {
            "name": "Failure case",
            "conditions": {
                "logic": "AND",
                "conditions": [
                    {"param": "REF:user.active", "operator": "equals", "value": True},
                    {"param": "REF:user.level", "operator": "equals", "value": "superuser"}  # False
                ]
            },
            "expected": False
        },
        
        # Test exists/not_exists
        {
            "name": "Exists operators",
            "conditions": [
                {"param": "REF:user.active", "operator": "exists"},
                {"param": "REF:nonexistent.field", "operator": "not_exists"}
            ],
            "expected": False  # Second condition will fail with exception, returning False
        },
        
        # Empty conditions (should pass)
        {
            "name": "Empty conditions",
            "conditions": [],
            "expected": True
        },
        
        # Empty group (should pass)
        {
            "name": "Empty group",
            "conditions": {
                "logic": "AND",
                "conditions": []
            },
            "expected": True
        }
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        try:
            result = evaluator.evaluate(test_case["conditions"])
            if result == test_case["expected"]:
                print(f"✅ {test_case['name']}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_case['name']}: FAILED - expected {test_case['expected']}, got {result}")
                failed += 1
        except Exception as e:
            print(f"💥 {test_case['name']}: ERROR - {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    # Demonstrate usage
    print("\n" + "="*50)
    print("DEMONSTRATION")
    print("="*50)
    
    # Show how to use it
    demo_conditions = {
        "logic": "AND",
        "groups": [
            {
                "logic": "OR",
                "conditions": [
                    {"param": "REF:environment.type", "operator": "equals", "value": "development"},
                    {"param": "REF:override.enabled", "operator": "equals", "value": True}
                ]
            },
            {
                "conditions": [
                    {"param": "REF:user.active", "operator": "equals", "value": True}
                ]
            }
        ]
    }
    
    print("Demo condition structure:")
    import json
    print(json.dumps(demo_conditions, indent=2))
    
    result = evaluator.evaluate(demo_conditions)
    print(f"\nEvaluation result: {result}")

if __name__ == "__main__":
    run_tests()