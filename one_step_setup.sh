#!/usr/bin/env bash

set -e

function fail {
	# Print a newline to stderr and exit.
	echo >/dev/stderr
	exit 1
}

# Make sure we don't override an existing Pants installation.
if [ -f "pants.toml" ]; then
	echo A \`pants.toml\` file already exists in this directory. This installation script \
		needs to create a new \`pants.toml\` file. >/dev/stderr
	echo If you are trying to upgrade to a newer version of Pants, set the \`pants_version\` \
		setting in your existing \`pants.toml\` file. >/dev/stderr
	echo If you are trying to run the install process from scratch, delete the \`pants.toml\` \
		file and start again. >/dev/stderr
	fail
fi

if [ -f "pants" ]; then
	echo A file called \`pants\` already exists in this directory. This installation script \
		will overwrite this file. To proceed, either rename this file, or delete the \
		\`pants\` file. >/dev/stderr
	fail
fi

# Find the latest stable version from PyPI if not set at the command line.
if [ -z "$PANTS_VERSION" ]; then
	PANTS_VERSION=$(curl https://pypi.org/pypi/pantsbuild.pants/json |
		grep -o '"version":"[^"]*"' |
		grep -o "[0-9]*\.[0-9]*\.[0-9]*")
fi

# Create enough of a pants.toml file that our bootstrap process can run
printf '[GLOBAL]\npants_version = "'$PANTS_VERSION'"\n' >pants.toml

# Fetch the Pants bootstrap script and run it to verify that we fetched
# the correct version
curl -L -O https://static.pantsbuild.org/setup/pants
chmod +x ./pants
PANTS_EXEC_VERSION=$(./pants --version)

# Verify that the correct version of Pants was installed.
if [ $PANTS_VERSION != $PANTS_EXEC_VERSION ]; then
	echo Pants was installed, but the version was $PANTS_EXEC_VERSION, not \
		$PANTS_VERSION. >/dev/stderr
	echo Consider filing an issue at https://github.com/pantsbuild/setup/issues/new >/dev/stderr
	fail
fi

# Let the user know that everything worked
echo >/dev/stderr
echo Pants was installed successfully\! >/dev/stderr
echo >/dev/stderr
