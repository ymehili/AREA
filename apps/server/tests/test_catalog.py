from app.integrations import catalog


def test_get_service_catalog_returns_constant():
    service_catalog = catalog.get_service_catalog()
    assert service_catalog is catalog.SERVICE_CATALOG
    assert len(service_catalog) > 0


def test_service_catalog_payload_shape_matches_dataclasses():
    payload = catalog.service_catalog_payload()
    assert isinstance(payload, list)
    assert len(payload) == len(catalog.SERVICE_CATALOG)

    for service_dataclass, service_payload in zip(catalog.SERVICE_CATALOG, payload, strict=True):
        assert service_payload["slug"] == service_dataclass.slug
        assert service_payload["name"] == service_dataclass.name
        assert service_payload["description"] == service_dataclass.description

        actions = service_payload["actions"]
        reactions = service_payload["reactions"]
        assert isinstance(actions, list)
        assert isinstance(reactions, list)
        assert actions, "actions should not be empty"
        assert reactions, "reactions should not be empty"

        for option, option_payload in zip(service_dataclass.actions, actions, strict=True):
            assert option_payload == {
                "key": option.key,
                "name": option.name,
                "description": option.description,
            }

        for option, option_payload in zip(service_dataclass.reactions, reactions, strict=True):
            assert option_payload == {
                "key": option.key,
                "name": option.name,
                "description": option.description,
            }

        # Ensure the original dataclasses remain tuples of dataclass instances
        assert service_dataclass.actions and isinstance(service_dataclass.actions[0].key, str)
        assert service_dataclass.reactions and isinstance(service_dataclass.reactions[0].key, str)
