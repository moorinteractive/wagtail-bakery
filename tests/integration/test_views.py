import pytest
from django.conf import settings

from wagtailbakery.views import (
    AllPagesView, AllPublishedPagesView, SitemapBuildableView, WagtailBakeryView)


@pytest.mark.django_db
def test_wagtail_bakery_view_get_url(page_tree):
    view = WagtailBakeryView()

    # Check url for homepage
    url = view.get_url(page_tree)
    assert url == '/'

    # Check child url for first child page
    child_page = page_tree.get_descendants().first()
    url = view.get_url(child_page)
    assert url == '/first/'

    # Check child url of the first child page
    child_page = child_page.get_descendants().first()
    url = view.get_url(child_page)
    assert url == '/first/first/'


@pytest.mark.django_db
def test_wagtail_bakery_view_build_path(page_tree):
    view = WagtailBakeryView()

    # Check build path for homepage
    build_path = view.get_build_path(page_tree)
    assert build_path == settings.BUILD_DIR + '/index.html'

    # Check child build path for first child page
    child_page = page_tree.get_descendants().first()
    build_path = view.get_build_path(child_page)
    assert build_path == settings.BUILD_DIR + '/first/index.html'

    # Check child build path of the first child page
    child_page = child_page.get_descendants().first()
    build_path = view.get_build_path(child_page)
    assert build_path == settings.BUILD_DIR + '/first/first/index.html'


@pytest.mark.django_db
def test_wagtail_bakery_view_build_path_for_multisite(multisite):
    view = WagtailBakeryView()
    site = multisite[0]
    page = site.root_page

    # Check build path for homepage
    build_path = view.get_build_path(page)
    assert build_path == '%s/index.html' % (
        settings.BUILD_DIR)


@pytest.mark.django_db
def test_all_published_pages_for_single_page(page):
    view = AllPublishedPagesView()
    qs = view.get_queryset()

    # Check if published page is returned
    assert qs.filter(id=page.id).exists()

    # Check if there are no unpublished pages returned
    page.live = False
    page.save()
    assert not qs.filter(live=False).exists()
    assert not qs.filter(id=page.id).exists()


@pytest.mark.django_db
def test_all_published_pages_for_multiple_pages(page_tree):
    view = AllPublishedPagesView()
    qs = view.get_queryset()

    # Check if all pages in page tree are returned
    assert qs.count() == 6


@pytest.mark.django_db
def test_all_pages_for_single_page(page):
    view = AllPagesView()
    qs = view.get_queryset()

    # Check if published page is returned
    assert qs.filter(id=page.id).exists()

    # Check if there are still unpublished pages returned
    page.live = False
    page.save()
    assert qs.filter(live=False).exists()
    assert qs.filter(id=page.id).exists()


@pytest.mark.django_db
def test_sitemap_content_for_single_site(settings, site):
    view = SitemapBuildableView()
    view.request = view.create_request(view.sitemap_path)

    content = view.get_content().decode()
    expected_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '<url><loc>{}</loc></url>\n'
        '</urlset>\n'
    ).format(site.root_page.get_full_url())

    assert content == expected_content


@pytest.mark.django_db
def test_sitemap_content_for_multiple_sites(settings, multisite):
    settings.BAKERY_MULTISITE = True
    view = SitemapBuildableView()

    for site in multisite:
        view.request = view.create_request(site, view.sitemap_path)

        content = view.get_content().decode()
        expected_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            '<url><loc>{}</loc></url>\n'
            '</urlset>\n'
        ).format(site.root_page.get_full_url())

        assert content == expected_content


@pytest.mark.django_db
def test_sitemap_build_path_for_single_site(settings, site):
    view = SitemapBuildableView()

    build_path = view.get_build_path(site)
    expected_build_path = view.sitemap_path

    assert build_path == expected_build_path


@pytest.mark.django_db
def test_sitemap_build_path_for_multiple_sites(settings, multisite):
    settings.BAKERY_MULTISITE = True
    view = SitemapBuildableView()

    build_paths = []
    expected_build_paths = []

    for site in multisite:
        build_paths.append(view.get_build_path(site))

        expected_build_paths.append("{hostname}/{sitemap_path}".format(
            hostname=site.hostname, sitemap_path=view.sitemap_path
        ))

    assert build_paths == expected_build_paths
