#!/usr/bin/env bash

PYTHON=${PYTHON:-$(which python2.7)}

PANTS_HOME="${PANTS_HOME:-${HOME}/.pants.d}"
PANTS_BOOTSTRAP="${PANTS_HOME}/bootstrap"
PANTS_REQUIREMENT="pantsbuild.pants"

VENV_VERSION=1.11.6

VENV_PACKAGE=virtualenv-${VENV_VERSION}
VENV_TARBALL=${VENV_PACKAGE}.tar.gz

# grab pants version from pants.ini or fail
# check for a venv via a naming/path convention and execute if found
# otherwise create venv and re-exec self

function tempdir {
  mktemp -d -p "$1" pants.XXXXXX 
}

# TODO(John Sirois): GC race loser tmp dirs leftover from bootstrap_XXX
# functions.  Any tmp dir w/o a symlink pointing to it can go.

function bootstrap_venv {
  if [[ ! -d "${PANTS_BOOTSTRAP}/${VENV_PACKAGE}" ]]
  then
    (
      mkdir -p "${PANTS_BOOTSTRAP}" && \
      staging_dir=$(tempdir "${PANTS_BOOTSTRAP}") && \
      cd ${staging_dir} && \
      curl -O https://pypi.python.org/packages/source/v/virtualenv/${VENV_TARBALL} && \
      tar -xzf ${VENV_TARBALL} && \
      ln -s "${staging_dir}/${VENV_PACKAGE}" "${staging_dir}/latest" && \
      mv -T "${staging_dir}/latest" "${PANTS_BOOTSTRAP}/${VENV_PACKAGE}"
    ) 1>&2
  fi
  echo "${PANTS_BOOTSTRAP}/${VENV_PACKAGE}"
}

function bootstrap_pants {
  requirement="${PANTS_REQUIREMENT}"
  if [[ -n "$1" ]]
  then
    requirement="${requirement}==$1"
  fi
  
  pants_version="${1:-latest}"
  if [[ ! -d "${PANTS_BOOTSTRAP}/${PANTS_REQUIREMENT}-${pants_version}" ]]
  then 
    (
      venv_path="$(bootstrap_venv)" && \
      staging_dir=$(tempdir "${PANTS_BOOTSTRAP}") && \
      "${PYTHON}" "${venv_path}/virtualenv.py" "${staging_dir}/install" && \
      source "${staging_dir}/install/bin/activate" && \
      pip install "${requirement}" && \
      ln -s "${staging_dir}/install" "${staging_dir}/${pants_version}" && \
      mv -T "${staging_dir}/${pants_version}" "${PANTS_BOOTSTRAP}/${PANTS_REQUIREMENT}-${pants_version}"
    ) 1>&2
  fi
  echo "${PANTS_BOOTSTRAP}/${PANTS_REQUIREMENT}-${pants_version}"
}

pants_dir=$(bootstrap_pants) && \
exec "${pants_dir}/bin/pants" "$@"
