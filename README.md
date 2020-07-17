# Pants setup

This repository contains the bootstrap needed to get you up and running with Pants.

Follow the instructions at https://www.pantsbuild.org/docs/installation.

### Development

We use [tox](https://testrun.org/tox/en/latest/) for test automation. To run the test suite and linters, invoke tox:

```bash
$ tox
```

You may run certain checks (`environments` in tox) with `tox -e` (run `tox -a` to see all options):

```bash
$ tox -e format-run
$ tox -e lint
$ tox -e test
```

You may pass arguments to Pytest like this:

```bash
$ tox -e test -- -vv -k test_only_bootstraps_the_first_time
```
