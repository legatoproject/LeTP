.. _fixtures:

########
Fixtures
########

See the pytest documentation to understand the concept of fixtures: `Pytest fixture presentation <https://docs.pytest.org/en/stable/fixture.html#fixture>`_.
They allow to have dependency injections, to initialize the tests and clean them at the end.
They are declared in a "conftest.py" file and are passed as parameter of the tests.

To run your tests, "conftest.py" file needs to be at the root directory of your tests.
More information about conftest.py file can be found here: `conftest.py <https://docs.pytest.org/en/stable/fixture.html#conftest-py-sharing-fixtures-across-multiple-files>`_

Here are the main available fixtures in LeTP:

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   fixtures/global_fixtures.rst
   fixtures/target_fixtures.rst
   fixtures/legato_fixtures.rst
   fixtures/hardware_fixtures.rst


