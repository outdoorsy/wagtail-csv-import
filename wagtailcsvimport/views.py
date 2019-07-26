from django.http import Http404
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.utils.timezone import get_current_timezone_name

try:
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailcore.models import Page

from .exporting import export_pages
from .exporting import get_exportable_fields_for_model
from .forms import ExportForm
from .forms import ImportForm
from .forms import PageTypeForm
from .importing import Error
from .importing import import_pages


def index(request):
    return render(request, 'wagtailcsvimport/index.html')


def import_from_file(request):
    """Import pages from a CSV file.

    The CSV format is compatible with the one that the CSV exporter
    generates. This means it's possible to export pages to CSV, make
    changes and then import the file to bulk update them.

    Import is all-or-nothing. If there is at least one error then all
    changes will be rolled back.

    """
    successes = []
    errors = []
    csv_header_example = None
    import_form = None
    page_model = None

    if request.method == 'GET':
        page_type_form = PageTypeForm(request.GET)
        if page_type_form.is_valid():
            page_model = page_type_form.get_page_model()
            import_form = ImportForm()
    elif request.method == 'POST':
        page_type_form = PageTypeForm(request.POST)
        if page_type_form.is_valid():
            page_model = page_type_form.get_page_model()
            import_form = ImportForm(request.POST, request.FILES)
            if import_form.is_valid():
                try:
                    csv_file = import_form.cleaned_data['file'].read().decode('utf-8')
                except UnicodeDecodeError as e:
                    errors.append(Error('Error decoding file, make sure it\'s an UTF-8 encoded CSV file', e))
                else:
                    successes, errors = import_pages(csv_file.splitlines(), page_model)
                return render(request, 'wagtailcsvimport/import_from_file_results.html', {
                    'request': request,
                    'successes': successes,
                    'errors': errors,
                })

    if page_model:
        all_fields = get_exportable_fields_for_model(page_model)
        csv_header_example = ','.join(all_fields)

    return render(request, 'wagtailcsvimport/import_from_file.html', {
        'csv_header_example': csv_header_example,
        'import_form': import_form,
        'page_type_form': page_type_form,
        'request': request,
        'successes': successes,
        'errors': errors,
        'timezone': get_current_timezone_name(),
    })


def export_to_file(request):
    """Export a part of the page tree to a CSV file.

    User will see a form to choose one particular page type. If
    selected only pages of that type will be exported, and its
    specific fields could be selected. Otherwise only the base Page
    model's fields will be exported.

    HTTP response will be streamed, to reduce memory usage and avoid
    response timeouts.

    """
    export_form = None
    if request.method == 'GET':
        page_type_form = PageTypeForm(request.GET)
        if page_type_form.is_valid():
            page_model = page_type_form.get_page_model()
            export_form = ExportForm(page_model=page_model)
    elif request.method == 'POST':
        page_type_form = PageTypeForm(request.POST)
        if page_type_form.is_valid():
            content_type = page_type_form.get_content_type()
            page_model = content_type.model_class() if content_type else None
            export_form = ExportForm(request.POST, page_model=page_model)
            if export_form.is_valid():
                fields = export_form.cleaned_data['fields']
                only_published = export_form.cleaned_data['only_published']
                csv_rows = export_pages(
                    export_form.cleaned_data['root_page'],
                    content_type=content_type,
                    fieldnames=fields,
                    only_published=only_published
                )
                response = StreamingHttpResponse(csv_rows, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="wagtail_export.csv"'
                return response

    return render(request, 'wagtailcsvimport/export_to_file.html', {
        'export_form': export_form,
        'page_type_form': page_type_form,
        'request': request,
        'timezone': get_current_timezone_name(),
    })


def export(request, page_id, only_published=False):
    """
    API endpoint of this source site to export a part of the page tree
    rooted at page_id

    Requests are made by a destination site's import_from_api view.
    """
    if only_published:
        pages = Page.objects.live()
    else:
        pages = Page.objects.all()

    try:
        root_page = pages.get(pk=page_id)
    except Page.DoesNotExist:
        raise Http404

    csv_rows = export_pages(root_page, content_type=root_page.content_type,
                            only_published=only_published)
    response = StreamingHttpResponse(csv_rows, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="wagtail_export.csv"'
    return response
