from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry
from .models import Dispatch


@registry.register_document
class DispatchDocument(Document):
    class Index:
        name = 'dispatch_mashauri_fixed'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}

    class Django:
        model = Dispatch
        fields = [
            'site_fdt_cluster_link_name',
            'lepton_project_name',
            'project_type',
            'msp',
            'sla_timer',
            'status',
            'comments',
        ]
