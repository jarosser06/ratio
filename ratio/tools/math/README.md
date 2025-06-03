Math Tool
==========

Overview
--------
The Math Tool evaluates mathematical formulas with support for custom functions and element-wise operations on arrays. It provides a safe way to perform complex calculations using Python's math capabilities while supporting business-specific mathematical operations.

Functionality
-------------
- Evaluates mathematical expressions using standard Python math functions
- Supports custom function definitions for business logic
- Handles element-wise operations on lists automatically
- Uses simpleeval for safe formula evaluation
- Returns both scalar and array results

Standard Functions
------------------
The Math Tool includes all standard mathematical functions:

**Arithmetic**: `sum`, `max`, `min`, `abs`, `round`, `pow`  
**Math Functions**: `sqrt`, `exp`, `log`, `log10`, `sin`, `cos`, `tan`, `floor`, `ceil`  
**Statistics**: `mean`, `median`, `stdev`, `variance`  
**Utilities**: `len`

All functions support both scalar values and element-wise operations on lists.

Custom Functions
----------------
Define reusable business logic with custom functions:

```json
{
  "opportunity_score": {
    "params": ["revenue", "probability", "days_to_close"],
    "formula": "(revenue * probability) / max(days_to_close, 1)"
  },
  "compound_growth": {
    "params": ["principal", "rate", "years"],
    "formula": "principal * pow(1 + rate, years)"
  }
}
```

Custom functions automatically support element-wise operations when passed arrays.

Element-wise Operations
-----------------------
Functions work seamlessly with both scalars and arrays:

**Scalar**: `sin(1.57)` → `1.0`  
**Array**: `sin([0, 1.57, 3.14])` → `[0.0, 1.0, 0.0]`  
**Mixed**: `pow([2, 3, 4], 2)` → `[4, 9, 16]`

Tool Definition
----------------
```json
{
  "description": "Mathematical processor that evaluates formulas with custom functions and handles element-wise operations on arrays",
  "arguments": [
    {
      "name": "formula",
      "type_name": "string",
      "description": "Mathematical formula to evaluate",
      "required": true
    },
    {
      "name": "values",
      "type_name": "object",
      "description": "Dictionary of variable names and their values",
      "required": true
    },
    {
      "name": "function_definitions",
      "type_name": "object",
      "description": "Custom function definitions",
      "required": false,
      "default_value": {}
    },
    {
      "name": "result_file_path",
      "type_name": "string",
      "description": "Path where result should be saved",
      "required": false
    }
  ],
  "responses": [
    {
      "name": "result",
      "type_name": "any",
      "description": "The calculated result",
      "required": true
    },
    {
      "name": "result_file_path",
      "type_name": "file",
      "description": "Path to file containing calculation results",
      "required": true
    },
    {
      "name": "formula_used",
      "type_name": "string",
      "description": "The formula that was evaluated",
      "required": true
    },
    {
      "name": "functions_available",
      "type_name": "number",
      "description": "Number of functions available",
      "required": true
    }
  ],
  "system_event_endpoint": "ratio::tool::math::execution"
}
```

Usage Examples
--------------

### Basic Arithmetic
```json
// Input
{
  "formula": "sum([10, 20, 30]) * 0.1",
  "values": {}
}

// Result: 6.0
```

### Statistical Analysis
```json
// Input
{
  "formula": "mean(sales_data) + stdev(sales_data)",
  "values": {
    "sales_data": [1200, 1350, 1100, 1500, 1250]
  }
}

// Result: 1380.0 + 147.99 = 1527.99
```

### Custom Business Functions
```json
// Input
{
  "formula": "sum(opportunity_score(revenues, probabilities, days))",
  "values": {
    "revenues": [100000, 50000, 75000],
    "probabilities": [0.8, 0.6, 0.9],
    "days": [30, 45, 15]
  },
  "function_definitions": {
    "opportunity_score": {
      "params": ["revenue", "probability", "days_to_close"],
      "formula": "(revenue * probability) / max(days_to_close, 1)"
    }
  }
}

// Result: 7833.33
// Calculates weighted opportunity scores for each deal and sums them
```

### Financial Modeling
```json
// Input
{
  "formula": "stdev(compound_growth(investments, rates, years)) / mean(compound_growth(investments, rates, years))",
  "values": {
    "investments": [10000, 25000, 15000, 30000],
    "rates": [0.07, 0.05, 0.09, 0.06],
    "years": 10
  },
  "function_definitions": {
    "compound_growth": {
      "params": ["principal", "rate", "years"],
      "formula": "principal * pow(1 + rate, years)"
    }
  }
}

// Result: 0.3766
// Coefficient of variation for investment growth scenarios
```

### Complex Multi-Step Calculations
```json
// Input
{
  "formula": "sum(weighted_score(risk_adjusted_return(returns, risks, market_vol), weights))",
  "values": {
    "returns": [0.12, 0.08, 0.15, 0.10],
    "risks": [0.8, 0.6, 1.2, 0.7],
    "market_vol": 0.05,
    "weights": [0.3, 0.25, 0.25, 0.2]
  },
  "function_definitions": {
    "risk_adjusted_return": {
      "params": ["expected_return", "risk_factor", "market_volatility"],
      "formula": "expected_return - (risk_factor * market_volatility)"
    },
    "weighted_score": {
      "params": ["value", "weight"],
      "formula": "value * weight"
    }
  }
}

// Result: 0.0720
// Portfolio performance calculation with risk adjustment and weighting
```

### Outlier Detection
```json
// Input
{
  "formula": "max(abs(z_score(data_points, data_mean, data_std))) > threshold",
  "values": {
    "data_points": [23, 25, 28, 29, 29, 29, 30, 30, 31, 85],
    "data_mean": 33.0,
    "data_std": 17.65,
    "threshold": 2.0
  },
  "function_definitions": {
    "z_score": {
      "params": ["value", "mean_val", "std_dev"],
      "formula": "(value - mean_val) / std_dev"
    }
  }
}

// Result: true
// Detects if any data points are statistical outliers (z-score > 2.0)
```

### Trigonometric Analysis
```json
// Input
{
  "formula": "max(abs(weighted_score(sin(angles_rad), amplitude)))",
  "values": {
    "angles_rad": [0, 0.524, 0.785, 1.047, 1.571],
    "amplitude": 2.5
  },
  "function_definitions": {
    "weighted_score": {
      "params": ["value", "weight"],
      "formula": "value * weight"
    }
  }
}

// Result: 2.5
// Maximum amplitude of a scaled sine wave
```

Key Features
------------
- **Safe Evaluation**: Uses simpleeval to prevent code injection
- **Element-wise Operations**: Automatically handles arrays in functions
- **Custom Functions**: Define reusable business logic
- **Rich Standard Library**: All common math functions included
- **Flexible Input**: Supports complex nested formulas
- **Type Safety**: Validates inputs and outputs
- **Error Handling**: Clear error messages for debugging

Performance Notes
-----------------
- Custom functions are cached after first compilation
- Element-wise operations are optimized for large arrays
- Supports mixed scalar/array operations efficiently
- Memory usage scales linearly with array sizes