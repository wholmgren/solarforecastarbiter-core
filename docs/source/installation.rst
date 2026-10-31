.. _installation:

Installation
============

The ``solarforecastarbiter`` package is available on PyPI and conda-forge.

On PyPI::

    pip install solarforecastarbiter

Optional dependencies are specified with the following options:

    * ``fetch``: packages required for fetching NWP model grids.
    * ``plotting``: packages required for making plots and thus reports.
    * ``log``: packages required for logging using `Sentry.io <https://sentry.io>`_.
    * ``all``: all optional dependencies.

For example::

    pip install solarforecastarbiter[all]

The conda-forge package includes all optional dependencies::

    conda install -c conda-forge solarforecastarbiter

The package installation also includes the ``solararbiter`` :ref:`cli`.

The development environment is managed with `uv <https://docs.astral.sh/uv/>`_.
Fork and clone the repository, then from the root of the repository run::

    uv sync --all-extras

This creates a ``.venv`` with the package installed in editable mode, all
optional dependencies, and the ``test`` and ``lint`` dependency groups at the
versions in ``uv.lock``. Then run the tests and the linter::

    uv run pytest solarforecastarbiter
    uv run ruff check

A docker image is also available at
`quay.io <https://quay.io/repository/solararbiter/solarforecastarbiter-core>`_::

    docker pull quay.io/solararbiter/solarforecastarbiter-core