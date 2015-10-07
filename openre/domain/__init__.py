# -*- coding: utf-8 -*-

from openre.domain.local import Domain
from openre.domain.remote import RemoteDomainDummy

def create_domain_factory(
    local_domain_class=Domain,
    remote_domain_class=RemoteDomainDummy,
    local_domains=None
):
    """
    Создает фабрику доменов которая возвращает локальный или глобальный домен
    в зависимости от флага is_local
    """
    if local_domains is None:
        local_domains = []
    if not isinstance(local_domains, list):
        local_domains = [local_domains]
    def domain_factory(domain_name):
        is_local = not local_domains \
                or (local_domains and domain_name in local_domains)
        if not is_local:
            return remote_domain_class
        return local_domain_class
    return domain_factory
