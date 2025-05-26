import math
import statistics

from typing import Dict, List, Union, Any, Callable

from simpleeval import simple_eval


class MathProcessor:
    """
    Math processor that evaluates formulas with custom functions and standard math operations.
    Supports element-wise operations on lists for custom functions.
    """

    def _element_wise_wrapper(self, func: Callable) -> Callable:
        """
        Wrap standard functions to handle both scalars and lists

        Keyword arguments:
        func -- The function to wrap, which should accept a single argument
        """
        def wrapper(arg):
            if isinstance(arg, list):
                return [func(item) for item in arg]

            else:
                return func(arg)

        return wrapper

    def _binary_element_wise_wrapper(self, func: Callable) -> Callable:
        """
        Wrap binary functions to handle element-wise operations

        Keyword arguments:
        func -- The function to wrap, which should accept two arguments
        """
        def wrapper(arg1, arg2):
            # If both are lists, apply element-wise
            if isinstance(arg1, list) and isinstance(arg2, list):
                if len(arg1) != len(arg2):
                    raise ValueError("Both list arguments must have the same length")

                return [func(a, b) for a, b in zip(arg1, arg2)]

            # If one is list and other is scalar, apply scalar to all elements
            elif isinstance(arg1, list):
                return [func(a, arg2) for a in arg1]

            elif isinstance(arg2, list):
                return [func(arg1, b) for b in arg2]

            else:
                return func(arg1, arg2)

        return wrapper

    # Standard functions available in formulas
    STANDARD_FUNCTIONS = {
        # Built-in functions
        "sum": sum,
        "max": max,
        "min": min,
        "round": round,
        "len": len,

        # Math module functions
        "sqrt": math.sqrt,
        "pow": math.pow,
        "exp": math.exp,
        "log": math.log,
        "log10": math.log10,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "floor": math.floor,
        "ceil": math.ceil,

        # Statistics functions
        "mean": statistics.mean,
        "median": statistics.median,
        "stdev": statistics.stdev,
        "variance": statistics.variance,
    }

    def __init__(self, function_definitions: Dict[str, Dict] = None):
        """
        Initialize the math processor with custom function definitions.

        Keyword arguments:
        function_definitions -- Dictionary of custom function definitions
        """
        self.function_definitions = function_definitions or {}

        # Create element-wise versions of functions that need it
        self.enhanced_functions = self.STANDARD_FUNCTIONS.copy()

        # Create element-wise versions of functions that need it
        self.enhanced_functions = self.STANDARD_FUNCTIONS.copy()

        # Unary functions that should work element-wise on lists
        unary_element_wise = ["abs", "sqrt", "exp", "log", "log10", "sin", "cos", "tan", "floor", "ceil", "round"]

        for func_name in unary_element_wise:
            if func_name == "abs":
                self.enhanced_functions[func_name] = self._element_wise_wrapper(abs)

            elif func_name == "round":
                self.enhanced_functions[func_name] = self._element_wise_wrapper(round)

            elif func_name in ["sqrt", "exp", "log", "log10", "sin", "cos", "tan", "floor", "ceil"]:
                self.enhanced_functions[func_name] = self._element_wise_wrapper(getattr(math, func_name))

        # Binary functions that should work element-wise
        self.enhanced_functions["pow"] = self._binary_element_wise_wrapper(math.pow)

        self.custom_functions = self._build_custom_functions()

    def _build_custom_functions(self) -> Dict[str, Callable]:
        """
        Build executable custom functions from definitions
        
        Returns:
            Dictionary of custom function names to their callable implementations
        """
        custom_funcs = {}

        for func_name, definition in self.function_definitions.items():
            params = definition["params"]

            formula = definition["formula"]

            custom_funcs[func_name] = self._create_custom_function(params, formula, func_name)

        return custom_funcs

    def _create_custom_function(self, params: List[str], formula: str, func_name: str) -> Callable:
        """
        Create a custom function that supports element-wise operations on lists

        Keyword arguments:
        params -- List of parameter names for the function
        formula -- The formula string to evaluate
        func_name -- Name of the function being created

        Returns:
            A callable function that can be used in evaluations
        """

        def custom_func(*args):
            if len(args) != len(params):
                raise ValueError(f"Function {func_name} expects {len(params)} arguments, got {len(args)}")

            # Check if any arguments are lists
            list_args = [isinstance(arg, list) for arg in args]

            if any(list_args):
                # Ensure all list arguments have the same length
                list_lengths = [len(arg) for arg, is_list in zip(args, list_args) if is_list]

                if len(set(list_lengths)) > 1:
                    raise ValueError(f"All list arguments to {func_name} must have the same length")

                # Apply function element-wise
                if not list_lengths:
                    raise ValueError(f"No list arguments found in {func_name}")

                length = list_lengths[0]

                results = []

                for i in range(length):
                    # Build arguments for this iteration
                    iter_args = []

                    for arg, is_list in zip(args, list_args):
                        if is_list:
                            iter_args.append(arg[i])

                        else:
                            iter_args.append(arg)  # Scalar value used for all iterations

                    # Create namespace for this evaluation
                    namespace = dict(zip(params, iter_args))

                    # Evaluate formula with combined namespace
                    all_functions = {**self.enhanced_functions, **self.custom_functions}

                    result = simple_eval(formula, names=namespace, functions=all_functions)

                    results.append(result)

                return results

            else:
                # All scalar arguments - single evaluation
                namespace = dict(zip(params, args))

                all_functions = {**self.enhanced_functions, **self.custom_functions}

                return simple_eval(formula, names=namespace, functions=all_functions)

        return custom_func

    def evaluate(self, values: Dict[str, Any], formula: str) -> Union[float, int, List]:
        """
        Evaluate a formula with the given values.

        Keyword arguments:
        values -- Dictionary of variable names and their values
        formula -- The formula string to evaluate

        Returns:
            Result of the formula evaluation
        """
        # Combine all available functions
        all_functions = {**self.enhanced_functions, **self.custom_functions}

        try:
            result = simple_eval(formula, names=values, functions=all_functions)

            return result

        except Exception as e:
            raise ValueError(f"Error evaluating formula '{formula}': {str(e)}")

    def get_available_functions(self) -> Dict[str, str]:
        """
        Return a dictionary of all available functions and their descriptions

        Returns:
            Dictionary of function names to their descriptions
        """
        available = {}

        # Add standard functions
        for name in self.enhanced_functions:
            available[name] = f"Standard function: {name}"

        # Add custom functions
        for name, definition in self.function_definitions.items():
            params_str = ", ".join(definition['params'])

            available[name] = f"Custom function: {name}({params_str}) = {definition["formula"]}"

        return available