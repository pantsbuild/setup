# Copyright 2019 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

python_library(
  name = 'common',
  sources = 'common.py',
)

python_binary(
  name='ci',
  sources='ci.py',
  dependencies=[
    ':common',
  ],
)

python_binary(
  name='mypy',
  sources='mypy.py',
  dependencies=[
    ':common',
  ],
)

python_binary(
  name='shellcheck',
  sources='shellcheck.py',
  dependencies=[
    ':common',
  ],
)
