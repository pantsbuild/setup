# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

python_library(
  name = 'test_base',
  sources = 'test_base.py',
)

python_tests(
  name='first_time_install',
  sources='test_first_time_install.py',
  dependencies=[
    ':test_base',
  ],
)
