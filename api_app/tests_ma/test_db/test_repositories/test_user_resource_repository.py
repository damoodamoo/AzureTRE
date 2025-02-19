from mock import patch, MagicMock
import pytest

from db.errors import EntityDoesNotExist
from db.repositories.user_resources import UserResourceRepository
from models.domain.resource import ResourceType
from models.domain.user_resource import UserResource
from models.schemas.user_resource import UserResourceInCreate, UserResourcePatchEnabled


WORKSPACE_ID = "def000d3-82da-4bfc-b6e9-9a7853ef753e"
SERVICE_ID = "937453d3-82da-4bfc-b6e9-9a7853ef753e"
RESOURCE_ID = "000000d3-82da-4bfc-b6e9-9a7853ef753e"
USER_ID = "abc000d3-82da-4bfc-b6e9-9a7853ef753e"


@pytest.fixture
def basic_user_resource_request():
    return UserResourceInCreate(templateName="user-resource-type", properties={"display_name": "test", "description": "test", "tre_id": "test"})


@pytest.fixture
def user_resource_repo():
    with patch('azure.cosmos.CosmosClient') as cosmos_client_mock:
        yield UserResourceRepository(cosmos_client_mock)


@pytest.fixture
def user_resource():
    user_resource = UserResource(
        id=RESOURCE_ID,
        templateVersion="0.1.0",
        properties={},
        templateName="my-workspace-service",
        resourcePath="test"
    )
    return user_resource


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template')
@patch('core.config.TRE_ID', "9876")
def test_create_user_resource_item_creates_a_user_resource_with_the_right_values(validate_input_mock, user_resource_repo, basic_user_resource_request):
    user_resource_to_create = basic_user_resource_request
    validate_input_mock.return_value = basic_user_resource_request.templateName

    user_resource = user_resource_repo.create_user_resource_item(user_resource_to_create, WORKSPACE_ID, SERVICE_ID, "parent-service-type", USER_ID)

    assert user_resource.templateName == basic_user_resource_request.templateName
    assert user_resource.resourceType == ResourceType.UserResource
    assert user_resource.workspaceId == WORKSPACE_ID
    assert user_resource.parentWorkspaceServiceId == SERVICE_ID
    assert user_resource.ownerId == USER_ID
    assert len(user_resource.properties["tre_id"]) > 0
    # need to make sure request doesn't override system param
    assert user_resource.properties["tre_id"] != "test"


@patch('db.repositories.user_resources.UserResourceRepository.validate_input_against_template', side_effect=ValueError)
def test_create_user_resource_item_raises_value_error_if_template_is_invalid(_, user_resource_repo, basic_user_resource_request):
    with pytest.raises(ValueError):
        user_resource_repo.create_user_resource_item(basic_user_resource_request, WORKSPACE_ID, SERVICE_ID, "parent-service-type", USER_ID)


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
def test_get_user_resources_for_workspace_queries_db(query_mock, user_resource_repo):
    expected_query = f'SELECT * FROM c WHERE c.isActive != false AND c.resourceType = "user-resource" AND c.parentWorkspaceServiceId = "{SERVICE_ID}" AND c.workspaceId = "{WORKSPACE_ID}"'

    user_resource_repo.get_user_resources_for_workspace_service(WORKSPACE_ID, SERVICE_ID)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.user_resources.UserResourceRepository.query')
def test_get_user_resource_returns_resource_if_found(query_mock, user_resource_repo, user_resource):
    query_mock.return_value = [user_resource.dict()]

    actual_resource = user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)

    assert actual_resource == user_resource


@patch('db.repositories.user_resources.UserResourceRepository.query')
def test_get_user_resource_by_id_queries_db(query_mock, user_resource_repo, user_resource):
    query_mock.return_value = [user_resource.dict()]
    expected_query = f'SELECT * FROM c WHERE c.resourceType = "user-resource" AND c.parentWorkspaceServiceId = "{SERVICE_ID}" AND c.workspaceId = "{WORKSPACE_ID}" AND c.id = "{RESOURCE_ID}"'

    user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)

    query_mock.assert_called_once_with(query=expected_query)


@patch('db.repositories.user_resources.UserResourceRepository.query', return_value=[])
def test_get_user_resource_by_id_raises_entity_does_not_exist_if_not_found(_, user_resource_repo):
    with pytest.raises(EntityDoesNotExist):
        user_resource_repo.get_user_resource_by_id(WORKSPACE_ID, SERVICE_ID, RESOURCE_ID)


def test_patch_user_resource_updates_item(user_resource, user_resource_repo):
    user_resource_repo.update_item = MagicMock(return_value=None)
    user_resource_patch = UserResourcePatchEnabled(enabled=True)

    user_resource_repo.patch_user_resource(user_resource, user_resource_patch)
    user_resource.properties["enabled"] = False
    user_resource_repo.update_item.assert_called_once_with(user_resource)
