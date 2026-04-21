# Specify BDD Testing Framework Guide

**Specify** is a PHPSpec-like BDD (Behavior-Driven Development) testing framework for Python. It's a spec tool to describe your classes using a fluent, readable syntax.

## Installation

Already installed in your project via `uv add specify`.

```bash
source .venv/bin/activate
# or just use the activated terminal
```

## Basic Syntax

All specifications inherit from `ObjectBehavior` and follow these rules:

- **All test methods must start with `it_`**
- **All spec files must end with `_spec.py`**
- Test methods are chainable and fluent

## Basic Example

Create a file: `specs/calculator_spec.py`

```python
from specify import ObjectBehavior
from src.calculator import Calculator

class CalculatorSpec(ObjectBehavior):
    def _let(self):
        """Setup: describe the class and construct it"""
        self._describe(Calculator)
        self._be_constructed_with()

    def it_adds_numbers(self):
        """Test: verify addition works"""
        self.add(2, 3)._should_be(5)

    def it_multiplies_numbers(self):
        """Test: verify multiplication works"""
        self.multiply(2, 3)._should_be(6)
```

## Running Tests

```bash
# Run all specs in a file
python -m specify specs/calculator_spec.py

# Run all specs in a directory (finds all *_spec.py files)
python -m specify specs/

# Output is in TAP (Test Anything Protocol) format
```

### TAP Output Example

```
TAP version 13
1..2

ok 1 - CalculatorSpec: it adds numbers
ok 2 - CalculatorSpec: it multiplies numbers
```

### Pretty Output (Optional)

Install faucet for prettier TAP output:

```bash
npm install -g faucet
python -m specify specs/ | faucet
```

## Builtin Matchers

| Matcher | Checks | Alias |
|---------|--------|-------|
| `_should_be(value)` | `is` equality | `_should_return` |
| `_should_be_like(value)` | `==` equality | `_should_return_like` |
| `_should_not_be(value)` | `is not` | `_should_not_return` |
| `_should_not_be_like(value)` | `!=` | `_should_not_return_like` |
| `_should_be_an_instance_of(Type)` | `isinstance` | `_should_return_an_instance_of` |
| `_should_have_length(n)` | `len(x) == n` | |

## Matcher Examples

```python
def it_checks_values(self):
    self.get_value()._should_be_like(42)
    self.get_list()._should_have_length(3)
    self.get_object()._should_be_an_instance_of(dict)
    self.get_result()._should_not_be_like(None)
```

## Chainable/Fluent API

All matchers can be chained:

```python
def it_chains_assertions(self):
    self.calculate()._should_be_like(10)._should_be_an_instance_of(int)
```

## Custom Matchers

Define a `_matchers()` method to add custom assertions:

```python
from specify import ObjectBehavior

class MathSpec(ObjectBehavior):
    def _let(self):
        self._describe(SomeClass)

    def it_checks_custom_conditions(self):
        self.get_value()._should_be_positive()
        self.get_value()._should_be_even()

    def _matchers(self):
        def be_positive(value):
            return value > 0

        def be_even(value):
            return value % 2 == 0

        return {
            'be_positive': be_positive,
            'be_even': be_even,
        }
```

## Mocking with Prophepy

Specify integrates with **prophepy** for mocking (similar to Prophecy in PHPSpec).

### Mock Collaborators

```python
from specify import ObjectBehavior, mock
from src.calculator import Calculator
from src.displayer import Displayer

class DisplayerSpec(ObjectBehavior):

    @mock(Calculator)
    def _let(self, calculator_mock):
        """Setup with mocked Calculator"""
        self._describe(Displayer)
        self._be_constructed_with(calculator_mock)
        self.__calculator = calculator_mock

    def it_displays_addition(self):
        """Verify interaction with mocked calculator"""
        self.__calculator.add(2, 3)._will_return(5)
        self.__calculator.add(2, 3)._should_be_called()
        self.display_addition(2, 3)._should_be_like('2 + 3 = 5')
```

### Mock Internal Module Calls

```python
from specify import ObjectBehavior, mock_internal

class FileSpec(ObjectBehavior):
    @mock_internal('getcwd', lambda: '/fake/path', from_module='os')
    def it_uses_current_directory(self):
        # os.getcwd() will return '/fake/path' during this test
        self.get_directory()._should_be_like('/fake/path')
```

## Project Structure for Specs

Recommended layout:

```
ai-agent-platform-mvp/
├── src/
│   ├── agent.py
│   ├── connector.py
│   └── orchestrator.py
├── specs/
│   ├── agent_spec.py
│   ├── connector_spec.py
│   └── orchestrator_spec.py
└── pyproject.toml
```

## Full Example: Agent Spec

```python
from specify import ObjectBehavior, mock
from src.agent import Agent
from src.connector import Connector

class AgentSpec(ObjectBehavior):

    @mock(Connector)
    def _let(self, connector_mock):
        self._describe(Agent)
        self._be_constructed_with("reconciliation", connector_mock)
        self.__agent = self._get_subject()
        self.__connector = connector_mock

    def it_executes_tool_call(self):
        """Verify agent can execute a tool"""
        self.__connector.query("SELECT * FROM ledger")._will_return([{
            'id': 1,
            'amount': 100.00
        }])
        result = self.__agent.execute_tool('query_ledger')
        result._should_have_length(1)
        result[0]['amount']._should_be_like(100.00)

    def it_creates_session(self):
        """Verify agent session creation"""
        session = self.__agent.create_session()
        session._should_be_an_instance_of(dict)
        session._should_have_length(3)  # has id, status, created_at

    def _matchers(self):
        def be_valid_session_id(value):
            return isinstance(value, str) and len(value) > 0

        return {
            'be_valid_session_id': be_valid_session_id,
        }
```

## CI/CD Integration

Add to your CI pipeline:

```bash
#!/bin/bash
set -e

# Activate venv
source .venv/bin/activate

# Run all specs
python -m specify specs/

# Optional: pipe to faucet for prettier output
# python -m specify specs/ | faucet
```

## Tips & Best Practices

1. **One concept per spec method** — Keep `it_*` methods focused on a single behavior
2. **Use `_let()` for setup** — Initialize your objects and mocks in `_let()`
3. **Chainable assertions** — Use fluent style for readability
4. **Custom matchers** — Add domain-specific assertions in `_matchers()`
5. **Descriptive names** — `it_validates_account_number` is better than `it_validates`
6. **Mock external dependencies** — Use `@mock` for Connectors, APIs, databases
7. **Test behavior, not implementation** — Focus on what the class does, not how it does it

## Resources

- **GitHub:** https://github.com/Einenlum/specify
- **PHPSpec (inspiration):** https://github.com/phpspec/phpspec
- **TAP Format:** https://testanything.org/
- **Prophepy (mocking):** https://github.com/Einenlum/prophepy

## Commands Reference

```bash
# Run all specs in file
python -m specify specs/calculator_spec.py

# Run all specs in directory
python -m specify specs/

# Run with TAP output
python -m specify specs/ > test_results.tap

# Pretty TAP output (requires npm faucet)
python -m specify specs/ | faucet
```

---

**Next Steps:** Create your first spec file in `specs/` to test the Agent, Connector, or Orchestrator classes.
