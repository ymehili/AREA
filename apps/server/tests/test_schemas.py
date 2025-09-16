from app.integrations.catalog import SERVICE_CATALOG, AutomationOption, ServiceIntegration
from app.schemas.services import ServiceCatalogResponse


def test_service_catalog_response_from_catalog_uses_schema_models():
    response = ServiceCatalogResponse.from_catalog(SERVICE_CATALOG)

    assert response.services
    assert len(response.services) == len(SERVICE_CATALOG)

    for schema_service, dataclass_service in zip(response.services, SERVICE_CATALOG, strict=True):
        assert schema_service.slug == dataclass_service.slug
        assert schema_service.name == dataclass_service.name
        assert schema_service.description == dataclass_service.description
        assert len(schema_service.actions) == len(dataclass_service.actions)
        assert len(schema_service.reactions) == len(dataclass_service.reactions)

        for schema_action, dataclass_action in zip(
            schema_service.actions, dataclass_service.actions, strict=True
        ):
            assert schema_action.key == dataclass_action.key
            assert schema_action.name == dataclass_action.name
            assert schema_action.description == dataclass_action.description


def test_service_catalog_response_handles_empty_catalog():
    empty_catalog: tuple[ServiceIntegration, ...] = ()
    response = ServiceCatalogResponse.from_catalog(empty_catalog)
    assert response.services == []


def test_schema_accepts_dataclass_like_objects():
    custom_service = ServiceIntegration(
        slug="custom",
        name="Custom",
        description="Custom integration",
        actions=(
            AutomationOption(key="do", name="Do", description="Do something"),
        ),
        reactions=(
            AutomationOption(key="undo", name="Undo", description="Undo something"),
        ),
    )

    response = ServiceCatalogResponse.from_catalog((custom_service,))
    service = response.services[0]
    assert service.slug == "custom"
    assert service.actions[0].key == "do"
    assert service.reactions[0].key == "undo"
