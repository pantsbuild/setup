# Pants setup

This repository contains the bootstrap needed to get you up and running with pants.

Follow the instructions at https://www.pantsbuild.org/install.

### Development

We use [tox](https://testrun.org/tox/en/latest/) for test automation. To run the test suite and linters, invoke tox:

```bash
$ tox
```

You may run certain environments with `tox -e` (run `tox -a` to see all options):

```bash
$ tox -e format-run
$ tox -e lint
$ tox -e test
```
