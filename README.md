# wagtail-csv-import
Page export from one Wagtail instance into another.

A CSV with columns matching the fields of you page model can be imported into a destination site under an existing page.

The destination site should have the same page models as the source site, with compatible migrations.

## Installation

    pip install wagtail-csv-import

Now add to your project's `INSTALLED_APPS`:

    INSTALLED_APPS = [
        # ...
        'wagtailcsvimport',
        # ...
    ]

You should now see an 'CVS Import' item in the Wagtail admin menu.
