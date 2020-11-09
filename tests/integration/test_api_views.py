import json

import pytest
from wagtail import VERSION as WAGTAIL_VERSION

from wagtailbakery.api_views import (
    PagesAPIDetailView, PagesAPIListingView, TypedPagesAPIListingView)

from ..models import EventPage

DEFAULT_PAGE_FIELDS = {'id', 'meta', 'title'}
DEFAULT_PAGE_META_FIELDS = {'type', 'show_in_menus', 'search_description', 'first_published_at', 'slug', 'html_url', 'seo_title'}

if WAGTAIL_VERSION >= (2, 11):
    DEFAULT_PAGE_META_FIELDS.add('locale')


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_detail_view_contains_no_root_pages():
    """
    Do not include the Root page
    """
    view = PagesAPIDetailView()
    assert not any(o for o in view.get_queryset() if o.depth <= 1)


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_detail_view(page_tree):
    view = PagesAPIDetailView()

    # Check build path
    build_path = view.get_build_path(page_tree)
    assert build_path == 'api/pages/detail/2.json'

    # Check child build path for first child page
    child_page = page_tree.get_descendants().first()
    build_path = view.get_build_path(child_page)
    assert build_path == 'api/pages/detail/3.json'

    # Check child build path of the first child page
    child_page = child_page.get_descendants().first()
    build_path = view.get_build_path(child_page)
    assert build_path == 'api/pages/detail/6.json'


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_detail_view_build_path_for_multisite(multisite):
    view = PagesAPIDetailView()
    site = multisite[0]
    page = site.root_page

    # Check build path for homepage
    build_path = view.get_build_path(page)
    assert build_path == 'api/pages/detail/2.json'


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_detail_view_content(page_tree):
    view = PagesAPIDetailView()

    # Check content for homepage
    content = json.loads(view.get_content(page_tree).decode('UTF-8'))
    assert set(content.keys()) == DEFAULT_PAGE_FIELDS
    assert set(content['meta'].keys()) == DEFAULT_PAGE_META_FIELDS.union({'parent'})
    assert content['id'] == 2
    assert content['title'] == "Welcome to your new Wagtail site!"

    # Check content for first child page
    child_page = page_tree.get_descendants().first()
    content = json.loads(view.get_content(child_page).decode('UTF-8'))
    assert set(content.keys()) == DEFAULT_PAGE_FIELDS
    assert set(content['meta'].keys()) == DEFAULT_PAGE_META_FIELDS.union({'parent'})
    assert content['id'] == 3
    assert content['title'] == "Page"

    # Check content of the first grandchild page
    grandchild_page = child_page.get_descendants().first()
    content = json.loads(view.get_content(grandchild_page).decode('UTF-8'))
    assert set(content.keys()) == DEFAULT_PAGE_FIELDS
    assert set(content['meta'].keys()) == DEFAULT_PAGE_META_FIELDS.union({'parent'})
    assert content['id'] == 6
    assert content['title'] == "Page"


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_listing_view():
    view = PagesAPIListingView()

    # Check build path
    build_path = view.get_build_path(0)
    assert build_path == 'api/pages/0.json'

    # Check build path for second page
    build_path = view.get_build_path(1)
    assert build_path == 'api/pages/1.json'


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_listing_view_build_path_for_multisite(multisite):
    view = PagesAPIListingView()

    # Check build path for homepage
    build_path = view.get_build_path(0)
    assert build_path == 'api/pages/0.json'


@pytest.mark.django_db
def test_wagtail_bakery_pages_api_listing_view_content(page_tree):
    view = PagesAPIListingView()

    # Check content
    content = json.loads(view.get_content(0)[0].decode('UTF-8'))
    assert set(content.keys()) == {'meta', 'items'}
    assert set(content['meta'].keys()) == {'total_count'}

    page = content['items'][0]
    assert set(page.keys()) == DEFAULT_PAGE_FIELDS
    assert set(page['meta'].keys()) == DEFAULT_PAGE_META_FIELDS


@pytest.mark.django_db
def test_wagtail_bakery_typed_pages_api_listing_view():
    view = TypedPagesAPIListingView()

    # Check build path
    build_path = view.get_build_path(EventPage, 0)
    assert build_path == 'api/pages/tests_EventPage/0.json'

    # Check build path for second page
    build_path = view.get_build_path(EventPage, 1)
    assert build_path == 'api/pages/tests_EventPage/1.json'


@pytest.mark.django_db
def test_wagtail_bakery_typed_pages_api_listing_view_build_path_for_multisite(multisite):
    view = TypedPagesAPIListingView()

    # Check build path for homepage
    build_path = view.get_build_path(EventPage, 0)
    assert build_path == 'api/pages/tests_EventPage/0.json'


@pytest.mark.django_db
def test_wagtail_bakery_typed_pages_api_listing_view_content(page_tree):
    view = TypedPagesAPIListingView()

    page_tree.add_child(instance=EventPage(
        title="Test event page",
        slug="test-event-page",
    ))

    # Check content
    content = json.loads(view.get_content(EventPage, 0)[0].decode('UTF-8'))
    assert set(content.keys()) == {'meta', 'items'}
    assert set(content['meta'].keys()) == {'total_count'}

    page = content['items'][0]
    assert set(page.keys()) == DEFAULT_PAGE_FIELDS
    assert set(page['meta'].keys()) == DEFAULT_PAGE_META_FIELDS
    assert page['title'] == "Test event page"
