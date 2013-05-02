from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse
from preserialize.serialize import serialize
from avocado.models import DataConcept
from avocado.conf import OPTIONAL_DEPS
from serrano.resources.field import FieldResource
from .base import BaseResource
from . import templates

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

# Shortcuts defined ahead of time for transparency
can_change_concept = lambda u: u.has_perm('avocado.change_dataconcept')


class ConceptBase(BaseResource):
    param_defaults = {
        'query': '',
    }

    template = templates.Concept

    def get_queryset(self, request):
        queryset = DataConcept.objects.all()
        if not can_change_concept(request.user):
            queryset = queryset.published()
        return queryset

    def get_object(self, request, **kwargs):
        queryset = self.get_queryset(request)
        try:
            return queryset.get(**kwargs)
        except DataConcept.DoesNotExist:
            pass

    @classmethod
    def prepare(self, request, instance):
        uri = request.build_absolute_uri
        obj = serialize(instance, **self.template)

        fields = []
        for cfield in instance.concept_fields.select_related('field').iterator():
            field = FieldResource.prepare(request, cfield.field)
            # Add the alternate name specific to the relationship between the
            # concept and the field.
            field.update(serialize(cfield, **templates.ConceptField))
            fields.append(field)

        obj['fields'] = fields
        obj['_links'] = {
            'self': {
                'rel': 'self',
                'href': uri(reverse('serrano:concept', args=[instance.pk])),
            }
        }
        return obj

    def is_forbidden(self, request, response, *args, **kwargs):
        "Ensure non-privileged users cannot make any changes."
        if request.method not in SAFE_METHODS and not can_change_concept(request.user):
            return True

    def is_not_found(self, request, response, pk, *args, **kwargs):
        instance = self.get_object(request, pk=pk)
        if instance is None:
            return True
        request.instance = instance
        return False


class ConceptResource(ConceptBase):
    "Concept Resource"
    def get(self, request, pk):
        return self.prepare(request, request.instance)


class ConceptsResource(ConceptBase):
    def is_not_found(self, request, response, *args, **kwargs):
        return False

    def get(self, request, pk=None):
        params = self.get_params(request)

        sort = params.get('sort')               # default: model ordering
        direction = params.get('direction')     # default: desc
        published = params.get('published')
        archived = params.get('archived')

        # This is only application if Haystack is setup
        if OPTIONAL_DEPS['haystack']:
            query = params.get('query').strip()
        else:
            query = ''

        queryset = self.get_queryset(request)

        # For privileged users, check if any filters are applied
        if can_change_concept(request.user):
            filters = {}

            if published == 'true':
                filters['published'] = True
            elif published == 'false':
                filters['published'] = False

            if archived == 'true':
                filters['archived'] = True
            elif archived == 'false':
                filters['archived'] = False

            if filters:
                queryset = queryset.filter(**filters)
        # For non-privileged users, filter out the non-published and archived
        else:
            queryset = queryset.published()

        # If there is a query parameter, perform the search
        if query:
            results = DataConcept.objects.search(query, queryset)
            objects = map(lambda x: x.object, results)
        else:
            # Apply sorting
            if sort == 'name':
                if direction == 'asc':
                    queryset = queryset.order_by('name')
                else:
                    queryset = queryset.order_by('-name')
            objects = queryset.iterator()

        return map(lambda x: self.prepare(request, x), objects)


concept_resource = ConceptResource()
concepts_resource = ConceptsResource()

# Resource endpoints
urlpatterns = patterns('',
    url(r'^$', concepts_resource, name='concepts'),
    url(r'^(?P<pk>\d+)/$', concept_resource, name='concept'),
)