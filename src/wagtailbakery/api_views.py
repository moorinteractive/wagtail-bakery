import json
import logging
import os

from bakery.views import BuildableMixin
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.core.models import Page, Site

logger = logging.getLogger(__name__)

BAKERY_RESULTS_PER_PAGE = getattr(settings, 'BAKERY_RESULTS_PER_PAGE', 20)


class APIResponseError(Exception):
    pass


def handle_api_error(response):
    if response.status_code == 400:
        raise APIResponseError("API error: " + json.loads(response.render().content.decode('UTF-8'))['message'])

    raise APIResponseError("Unexpected status code returned from API: %d" % response.status_code)


class APIListingView(BuildableMixin):
    results_per_page = BAKERY_RESULTS_PER_PAGE

    @property
    def build_method(self):
        return self.build

    def get_build_path(self, page_num):
        """
        Override this to return the path of the file to be built
        """
        raise NotImplementedError

    def build(self):
        page_num = 0
        has_next_page = True

        while has_next_page:
            build_path = self.get_build_path(page_num + 1)
            self.prep_directory(build_path)

            page_content, has_next_page = self.get_content(page_num)

            path = os.path.join(settings.BUILD_DIR, build_path)
            self.build_file(path, page_content)

            page_num += 1


class APIDetailView(BuildableMixin):
    """
    Render and build a "detail" view of an object.

    Required attributes:

        endpoint_class:
            The Wagtail API endpoint class to use for generating the
            JSON documents

        get_queryset:
            A method that returns a queryset of objects to include
    """
    @property
    def build_method(self):
        return self.build_queryset

    def get_build_path(self, obj):
        """
        Override this to return the path of the file to be built
        """
        raise NotImplementedError

    def build_object(self, obj):
        build_path = self.get_build_path(obj)
        self.prep_directory(build_path)

        page_content = self.get_content(obj)

        path = os.path.join(settings.BUILD_DIR, build_path)
        self.build_file(path, page_content)

    def build_queryset(self):
        [self.build_object(o) for o in self.get_queryset()]

    def unbuild_object(self, obj):
        """
        Deletes the file at self.get_build_path()
        """
        logger.debug("Unbuilding %s" % obj)
        target_path = os.path.join(settings.BUILD_DIR, self.get_build_path(obj))
        if self.fs.exists(target_path):
            logger.debug("Removing {}".format(target_path))
            self.fs.remove(target_path)

    def get_content(self, obj):
        # Create a dummy request
        request = self.create_request('/?format=json&fields=*')
        request.wagtailapi_router = WagtailAPIRouter('')

        response = self.endpoint_class.as_view({'get': 'detail_view'})(request, pk=obj.pk)

        if response.status_code == 200:
            return response.render().content

        handle_api_error(response)


class PagesAPIDetailView(APIDetailView):
    """
    Builds detail documents for every published page.

    URL example: /api/pages/detail/1.json
    """
    endpoint_class = PagesAPIViewSet

    def get_build_path(self, page):
        return 'api/pages/detail/{pk}.json'.format(pk=page.pk)

    def get_queryset(self):
        if getattr(settings, 'BAKERY_MULTISITE', False):
            return Page.objects.filter(depth__gt=1).public().live()
        else:
            site = Site.objects.get(is_default_site=True)
            return site.root_page.get_descendants(inclusive=True).public().live()


class PagesAPIListingView(APIListingView):
    """
    Builds a single listing that lists every published page.

    URL example: /api/pages/1.json
    """
    def get_build_path(self, page_num):
        return 'api/pages/{page_num}.json'.format(page_num=page_num)

    def fetch_page_listing(self, page_num, model=None):
        if model:
            url = '/?format=json&fields=*&limit={}&offset={}&type={}.{}'.format(self.results_per_page, self.results_per_page * page_num, model._meta.app_label, model.__name__)
        else:
            url = '/?format=json&fields=*&limit={}&offset={}'.format(self.results_per_page, self.results_per_page * page_num)

        request = self.create_request(url)
        request.wagtailapi_router = WagtailAPIRouter('')
        response = PagesAPIViewSet.as_view({'get': 'listing_view'})(request)

        if response.status_code == 200:
            content = response.render().content
            has_next_page = json.loads(content.decode('UTF-8'))['meta']['total_count'] > self.results_per_page * (page_num + 1)
            return content, has_next_page

        handle_api_error(response)

    def get_content(self, page_num):
        return self.fetch_page_listing(page_num)


class TypedPagesAPIListingView(PagesAPIListingView):
    """
    Builds a listing for each page type. Containing all published
    pages of that type.

    URL example: /api/pages/blog_BlogPage/1.json
    """
    def get_build_path(self, model, page_num):
        return 'api/pages/{app_label}_{class_name}/{page_num}.json'.format(
            app_label=model._meta.app_label,
            class_name=model.__name__,
            page_num=page_num,
        )

    def get_content(self, model, page_num):
        return self.fetch_page_listing(page_num, model=model)

    def get_page_models(self):
        return [
            content_type.model_class()
            for content_type in ContentType.objects.filter(id__in=Page.objects.values_list('content_type_id', flat=True))
        ]

    def build(self):
        for model in self.get_page_models():
            page_num = 0
            has_next_page = True

            while has_next_page:
                build_path = self.get_build_path(model, page_num + 1)
                self.prep_directory(build_path)

                page_content, has_next_page = self.get_content(model, page_num)

                path = os.path.join(settings.BUILD_DIR, build_path)
                self.build_file(path, page_content)

                page_num += 1
