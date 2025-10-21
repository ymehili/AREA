from app.integrations import catalog


def test_get_service_catalog_returns_constant():
    service_catalog = catalog.get_service_catalog()
    assert service_catalog is catalog.SERVICE_CATALOG
    assert len(service_catalog) > 0


def test_service_catalog_payload_shape_matches_dataclasses():
    payload = catalog.service_catalog_payload()
    assert isinstance(payload, list)
    assert len(payload) == len(catalog.SERVICE_CATALOG)

    for index, service_dataclass in enumerate(catalog.SERVICE_CATALOG):
        service_payload = payload[index]
        assert service_payload["slug"] == service_dataclass.slug
        assert service_payload["name"] == service_dataclass.name
        assert service_payload["description"] == service_dataclass.description

        actions = service_payload["actions"]
        reactions = service_payload["reactions"]
        assert isinstance(actions, list)
        assert isinstance(reactions, list)
        # Note: actions or reactions can be empty for some services (e.g., time, debug)
        assert actions or reactions, "service should have at least actions or reactions"

        for option_index, option in enumerate(service_dataclass.actions):
            option_payload = actions[option_index]
            assert option_payload == {
                "key": option.key,
                "name": option.name,
                "description": option.description,
                "params": option.params,
            }

        for option_index, option in enumerate(service_dataclass.reactions):
            option_payload = reactions[option_index]
            assert option_payload == {
                "key": option.key,
                "name": option.name,
                "description": option.description,
                "params": option.params,
            }

        # Ensure the original dataclasses remain tuples of dataclass instances
        if service_dataclass.actions:
            assert isinstance(service_dataclass.actions[0].key, str)
        if service_dataclass.reactions:
            assert isinstance(service_dataclass.reactions[0].key, str)

