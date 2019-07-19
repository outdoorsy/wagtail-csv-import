# wagtail-csv-import

Export and import Wagtail pages in CSV format directly through the admin interface.

Exporting has the following features:

- Select a page and export it and all its descendants.
- Optionally select a specific page model. In this case fields of that
  specific model will become available for exporting, otherwise only
  Wagtail's Page model's fields will be exportable.
- Select a subset of fields to export.
- Generated CSV is streamed via HTTP, reducing memory usage in the
  server and avoiding response timeouts.

## Installation

    $ pip install wagtail-csv-import

Now add to your project's `INSTALLED_APPS`:

    INSTALLED_APPS = [
        # ...
        'wagtailcsvimport',
        # ...
    ]

You should now see a 'CVS Import' item in the Wagtail admin menu.

## Developing

It is recommended you create a virtualenv and install whatever
packages you need for development there. This is a good start:

    $ python -m venv venv-wagtailcsvimport
    $ . venv-wagtailcsvimport/bin/activate
    (venv-wagtailcsvimport) $ pip install Django wagtail tox

### Testing

To run the tests you will need an appropriate Python version (3.6 or
3.7 right now) and either install the test requirements yourself or
use *tox*.

If you have a virtualenv with Django and wagtail you should be able to
just run `./runtests.py`.

If you have tox installed you can run `tox`. This will create multiple
environments with different dependencies and test the project in each
of them. Some environments might fail to be created if you lack the
proper Python versions installed.

#### Updating tests.models

When making changes to the test models the tests migrations need to be
recreated. Follow this procedure:

1. Make your changes to *tests/models.py*.
1. Delete *tests/migrations/0001_initial.py*. There is no need to add
   more migrations, as they are only run on the transient test DB.
1. Comment off the `wagtailcsvimport` entry in *tests/settings.py*.
1. Run `python -m django makemigrations tests` from the project root.
1. Revert the change to the *settings.py*.
