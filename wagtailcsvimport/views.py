from pprint import pprint
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils.translation import ungettext, ugettext_lazy as _

try:
    from wagtail.admin import messages
    from wagtail.core.models import Page
except ImportError:  # fallback for Wagtail <2.0
    from wagtail.wagtailadmin import messages
    from wagtail.wagtailcore.models import Page

from wagtailcsvimport.exporting import export_pages
from wagtailcsvimport.forms import ExportForm, ImportFromFileForm
from wagtailcsvimport.importing import import_pages


def index(request):
    return render(request, 'wagtailcsvimport/index.html')



def import_from_file(request):
    """
    Bulk create new pages based on fields defined in a CSV file

    The source site's base url and the source page id of the point in the
    tree to import defined what to import and the destination parent page
    defines where to import it to.
    """
    if request.method == 'POST':
        form = ImportFromFileForm(request.POST, request.FILES)
        if form.is_valid():
            import_data = form.cleaned_data['file'].read().decode('utf-8')
            parent_page = form.cleaned_data['parent_page']

            try:
                page_count = import_pages(import_data, parent_page)
            except Exception as e:
                pprint(vars(e))
                messages.error(request, _(
                    "Import failed: %(reason)s") % {'reason': e}
                )
            else:
                messages.success(request, ungettext(
                    "%(count)s page imported.",
                    "%(count)s pages imported.",
                    page_count) % {'count': page_count}
                )
            return redirect('wagtailadmin_explore', parent_page.pk)
    else:
        form = ImportFromFileForm()

    return render(request, 'wagtailcsvimport/import_from_file.html', {
        'form': form,
    })


def export_to_file(request):
    """
    Export a part of this source site's page tree to a JSON file
    on this user's filesystem for subsequent import in a destination
    site's Wagtail Admin
    """
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            payload = export_pages(form.cleaned_data['root_page'], export_unpublished=True)
            response = JsonResponse(payload)
            response['Content-Disposition'] = 'attachment; filename="export.json"'
            return response
    else:
        form = ExportForm()

    return render(request, 'wagtailcsvimport/export_to_file.html', {
        'form': form,
    })


def export(request, page_id, export_unpublished=False):
    """
    API endpoint of this source site to export a part of the page tree
    rooted at page_id

    Requests are made by a destination site's import_from_api view.
    """
    try:
        if export_unpublished:
            root_page = Page.objects.get(id=page_id)
        else:
            root_page = Page.objects.get(id=page_id, live=True)
    except Page.DoesNotExist:
        return JsonResponse({'error': _('page not found')})

    payload = export_pages(root_page, export_unpublished=export_unpublished)

    return JsonResponse(payload)
