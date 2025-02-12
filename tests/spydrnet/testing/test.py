def run(verbosity=1, doctest=False):
    """Run SpyDrNet tests.

    Parameters
    ----------
    verbosity: integer, optional
      Level of detail in test reports.  Higher numbers provide more detail.

    doctest: bool, optional
      True to run doctests in code modules
    """

    import pytest

    pytest_args = ["-l"]

    if verbosity and int(verbosity) > 1:
        pytest_args += ["-" + "v" * (int(verbosity) - 1)]

    if doctest:
        pytest_args += ["--doctest-modules"]

    pytest_args += ["--pyargs", "spydrnet"]

    try:
        code = pytest.main(pytest_args)
    except SystemExit as exc:
        code = exc.code

    return code == 0


if __name__ == "__main__":
    run()
