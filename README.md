# Pants setup

This repository contains the bootstrap needed to get you up and running with Pants.

Follow the instructions at https://www.pantsbuild.org/docs/installation.

### Development

We use Pants for test automation (so recursive!). To run the test suite, linters and formatters:

```bash
$ pants fmt lint check test ::
```
