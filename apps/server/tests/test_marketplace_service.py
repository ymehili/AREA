"""Tests for marketplace service layer."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.models.area import Area
from app.models.area_step import AreaStep
from app.models.marketplace_template import PublishedTemplate
from app.models.template_tag import TemplateTag
from app.models.user import User
from app.schemas.marketplace import TemplatePublishRequest
from app.services.marketplace import (
    AreaNotFoundError,
    TemplateAlreadyPublishedError,
    TemplateNotApprovedError,
    TemplateNotFoundError,
    UnauthorizedError,
    approve_template,
    clone_template,
    get_template_by_id,
    list_categories,
    list_tags,
    publish_template,
    reject_template,
    sanitize_template,
    search_templates,
)


@pytest.fixture()
def test_user(db_session: Session) -> User:
    """Create a test user."""
    user = User(
        email="testuser@example.com",
        hashed_password="dummy_hash",
        is_confirmed=True,
        confirmed_at=datetime.now(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def other_user(db_session: Session) -> User:
    """Create another test user."""
    user = User(
        email="otheruser@example.com",
        hashed_password="dummy_hash",
        is_confirmed=True,
        confirmed_at=datetime.now(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def test_area(db_session: Session, test_user: User) -> Area:
    """Create a test area."""
    area = Area(
        user_id=test_user.id,
        name="Test Automation",
        trigger_service="github",
        trigger_action="new_pull_request",
        trigger_params={"repo": "owner/repo"},
        reaction_service="gmail",
        reaction_action="send_email",
        reaction_params={"to": "test@example.com", "subject": "PR Notification"},
        enabled=True,
    )
    db_session.add(area)
    db_session.commit()
    db_session.refresh(area)
    return area


@pytest.fixture()
def test_area_with_steps(db_session: Session, test_area: Area) -> Area:
    """Create test area with steps."""
    step1 = AreaStep(
        area_id=test_area.id,
        step_type="action",
        order=0,
        service="discord",
        action="send_message",
        config={"message": "New PR!", "clientId": "step_1", "targets": []},
    )
    step2 = AreaStep(
        area_id=test_area.id,
        step_type="action",
        order=1,
        service="gmail",
        action="send_email",
        config={"subject": "PR Alert", "clientId": "step_2", "targets": ["step_1"]},
    )
    db_session.add_all([step1, step2])
    db_session.commit()
    db_session.refresh(test_area)
    return test_area


def test_sanitize_template_removes_credentials(db_session: Session, test_area: Area):
    """CRITICAL: Test that credential sanitization removes all sensitive data."""
    # Create steps with service_connection_id (should be removed)
    steps = [
        AreaStep(
            area_id=test_area.id,
            step_type="action",
            order=0,
            service="github",
            action="create_issue",
            config={
                "service_connection_id": "some-uuid-here",
                "title": "Test Issue",
                "access_token": "secret_token_123",
            },
        )
    ]
    
    # Sanitize template
    template_json = sanitize_template(test_area, steps)
    
    # CRITICAL: Verify no credentials in JSON
    template_str = json.dumps(template_json)
    assert "service_connection_id" not in template_str
    assert "access_token" not in template_str
    assert "encrypted_access_token" not in template_str
    
    # Verify placeholders exist
    assert "credential_placeholder" in template_json["trigger"]
    assert "{{user_credential:github}}" in template_json["trigger"]["credential_placeholder"]
    assert "credential_placeholder" in template_json["reaction"]
    assert "{{user_credential:gmail}}" in template_json["reaction"]["credential_placeholder"]


def test_publish_template_success(
    db_session: Session,
    test_user: User,
    test_area_with_steps: Area,
):
    """Test successful template publication."""
    request = TemplatePublishRequest(
        area_id=test_area_with_steps.id,
        title="Save Gmail Attachments to Google Drive",
        description="Automatically save email attachments from Gmail to your Google Drive folder.",
        long_description="A comprehensive workflow that monitors Gmail for new emails...",
        category="productivity",
        tags=["gmail", "google-drive", "automation"],
    )
    
    template = publish_template(db_session, test_user.id, request)
    
    assert template.id is not None
    assert template.title == request.title
    assert template.description == request.description
    assert template.category == "productivity"
    assert template.status == "approved"  # Templates are auto-approved
    assert template.visibility == "public"
    assert template.publisher_user_id == test_user.id
    assert template.original_area_id == test_area_with_steps.id
    assert len(template.tags) == 3
    
    # Verify template_json exists and is sanitized
    assert template.template_json is not None
    assert "trigger" in template.template_json
    assert "reaction" in template.template_json
    template_str = json.dumps(template.template_json)
    assert "service_connection_id" not in template_str


def test_publish_template_creates_tags(db_session: Session, test_user: User, test_area: Area):
    """Test that publishing creates new tags if they don't exist."""
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Test Template",
        description="A test template to verify tag creation functionality works correctly.",
        category="test",
        tags=["newtag1", "newtag2"],
    )
    
    template = publish_template(db_session, test_user.id, request)
    
    # Verify tags were created
    tag1 = db_session.query(TemplateTag).filter(TemplateTag.name == "newtag1").first()
    tag2 = db_session.query(TemplateTag).filter(TemplateTag.name == "newtag2").first()
    
    assert tag1 is not None
    assert tag1.usage_count == 1
    assert tag2 is not None
    assert tag2.usage_count == 1
    
    # Verify tags are associated with template
    assert len(template.tags) == 2
    tag_names = [t.name for t in template.tags]
    assert "newtag1" in tag_names
    assert "newtag2" in tag_names


def test_publish_template_increments_existing_tag_usage(
    db_session: Session,
    test_user: User,
    test_area: Area,
):
    """Test that using existing tags increments usage count."""
    # Create existing tag
    existing_tag = TemplateTag(name="popular", slug="popular", usage_count=5)
    db_session.add(existing_tag)
    db_session.commit()
    
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Test Template",
        description="A test template using an existing tag to verify usage count increment.",
        category="test",
        tags=["popular"],
    )
    
    template = publish_template(db_session, test_user.id, request)
    
    # Verify tag usage incremented
    db_session.refresh(existing_tag)
    assert existing_tag.usage_count == 6


def test_publish_template_area_not_found(db_session: Session, test_user: User):
    """Test publishing non-existent area raises AreaNotFoundError."""
    fake_area_id = uuid.uuid4()
    request = TemplatePublishRequest(
        area_id=fake_area_id,
        title="Test Template",
        description="This should fail because the area doesn't exist in the database.",
        category="test",
        tags=["test"],
    )
    
    with pytest.raises(AreaNotFoundError) as exc_info:
        publish_template(db_session, test_user.id, request)
    
    assert str(fake_area_id) in str(exc_info.value)


def test_publish_template_not_owner(
    db_session: Session,
    test_user: User,
    other_user: User,
    test_area: Area,
):
    """Test publishing someone else's area raises UnauthorizedError."""
    request = TemplatePublishRequest(
        area_id=test_area.id,  # Belongs to test_user
        title="Test Template",
        description="This should fail because other_user doesn't own this area.",
        category="test",
        tags=["test"],
    )
    
    with pytest.raises(UnauthorizedError) as exc_info:
        publish_template(db_session, other_user.id, request)
    
    assert "You can only publish your own workflows" in str(exc_info.value)


def test_publish_template_already_published(
    db_session: Session,
    test_user: User,
    test_area: Area,
):
    """Test publishing same area twice raises TemplateAlreadyPublishedError."""
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="First Publication",
        description="Publishing this area for the first time should work fine.",
        category="test",
        tags=["test"],
    )
    
    # First publish succeeds
    publish_template(db_session, test_user.id, request)
    
    # Second publish should fail
    request2 = TemplatePublishRequest(
        area_id=test_area.id,
        title="Second Publication",
        description="This second publication attempt should fail with error.",
        category="test",
        tags=["test"],
    )
    
    with pytest.raises(TemplateAlreadyPublishedError):
        publish_template(db_session, test_user.id, request2)


def test_search_templates_basic(db_session: Session, test_user: User, test_area: Area):
    """Test basic template search returns approved templates."""
    # Publish and approve a template
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Test Search Template",
        description="This template should appear in search results after approval.",
        category="productivity",
        tags=["test", "search"],
    )
    template = publish_template(db_session, test_user.id, request)
    template.status = "approved"
    db_session.commit()
    
    # Search
    results, total = search_templates(db_session, limit=10)
    
    assert total == 1
    assert len(results) == 1
    assert results[0].id == template.id


def test_search_templates_only_approved(db_session: Session, test_user: User, test_area: Area):
    """Test search only returns approved templates, not pending."""
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Pending Template",
        description="This template is pending approval and should not appear in search.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)

    # Manually set to pending (templates are auto-approved by default)
    template.status = "pending"
    db_session.commit()

    # Template is pending, should not appear
    results, total = search_templates(db_session, limit=10)

    assert total == 0
    assert len(results) == 0


def test_search_templates_by_category(db_session: Session, test_user: User, test_area: Area):
    """Test filtering templates by category."""
    # Create area for second template
    area2 = Area(
        user_id=test_user.id,
        name="Another Automation",
        trigger_service="gmail",
        trigger_action="new_email",
        reaction_service="discord",
        reaction_action="send_message",
        enabled=True,
    )
    db_session.add(area2)
    db_session.commit()
    
    # Publish two templates in different categories
    request1 = TemplatePublishRequest(
        area_id=test_area.id,
        title="Productivity Template",
        description="This is a productivity-focused automation template for testing category filters.",
        category="productivity",
        tags=["test"],
    )
    template1 = publish_template(db_session, test_user.id, request1)
    template1.status = "approved"
    
    request2 = TemplatePublishRequest(
        area_id=area2.id,
        title="Communication Template",
        description="This is a communication-focused automation template for testing category filters.",
        category="communication",
        tags=["test"],
    )
    template2 = publish_template(db_session, test_user.id, request2)
    template2.status = "approved"
    db_session.commit()
    
    # Search by category
    results, total = search_templates(db_session, category="productivity", limit=10)
    
    assert total == 1
    assert results[0].category == "productivity"


def test_clone_template_success(db_session: Session, test_user: User, test_area_with_steps: Area):
    """Test successful template cloning with ID remapping."""
    # Publish and approve template
    request = TemplatePublishRequest(
        area_id=test_area_with_steps.id,
        title="Cloneable Template",
        description="This template can be cloned to create a new workflow with remapped step IDs.",
        category="test",
        tags=["clone", "test"],
    )
    template = publish_template(db_session, test_user.id, request)
    template.status = "approved"
    db_session.commit()
    
    # Clone template
    cloned_area = clone_template(
        db_session,
        template_id=template.id,
        user_id=test_user.id,
        area_name="My Cloned Workflow",
    )
    
    assert cloned_area.id != test_area_with_steps.id
    assert cloned_area.name == "My Cloned Workflow"
    assert cloned_area.user_id == test_user.id
    assert cloned_area.enabled is False  # Should start disabled
    
    # Verify steps were cloned
    assert len(cloned_area.steps) == 2
    
    # Verify ID remapping worked (targets should reference new step IDs, not old clientIds)
    step2_config = cloned_area.steps[1].config
    if "targets" in step2_config:
        # Targets should be UUIDs, not "step_1"
        for target in step2_config["targets"]:
            assert "step_" not in target  # Should be UUID, not clientId


def test_clone_template_not_approved(
    db_session: Session,
    test_user: User,
    test_area: Area,
):
    """Test cloning non-approved template raises TemplateNotApprovedError."""
    # Publish template (auto-approved by default)
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Unapproved Template",
        description="This template is not approved and cannot be cloned yet.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)

    # Manually set to pending (templates are auto-approved by default)
    template.status = "pending"
    db_session.commit()

    # Attempt to clone
    with pytest.raises(TemplateNotApprovedError) as exc_info:
        clone_template(
            db_session,
            template_id=template.id,
            user_id=test_user.id,
            area_name="Should Fail",
        )

    assert "not approved" in str(exc_info.value)
    assert template.status in str(exc_info.value)


def test_clone_template_increments_counters(
    db_session: Session,
    test_user: User,
    test_area: Area,
):
    """Test cloning increments usage_count and clone_count."""
    # Publish and approve template
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Counter Test Template",
        description="This template tests that usage and clone counters increment properly.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)
    template.status = "approved"
    db_session.commit()
    
    initial_usage = template.usage_count
    initial_clones = template.clone_count
    
    # Clone template
    clone_template(
        db_session,
        template_id=template.id,
        user_id=test_user.id,
        area_name="Cloned Workflow",
    )
    
    # Refresh and check counters
    db_session.refresh(template)
    assert template.usage_count == initial_usage + 1
    assert template.clone_count == initial_clones + 1


def test_approve_template(db_session: Session, test_user: User, test_area: Area):
    """Test approving a template sets correct fields."""
    admin_user = User(
        email="admin@example.com",
        hashed_password="hash",
        is_admin=True,
        is_confirmed=True,
    )
    db_session.add(admin_user)
    db_session.commit()

    # Publish template (auto-approved by default)
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Pending Approval",
        description="This template is waiting for admin approval before going live.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)

    # Manually set to pending to test approval flow
    template.status = "pending"
    template.approved_at = None
    template.published_at = None
    db_session.commit()

    # Approve
    approved = approve_template(db_session, template.id, admin_user.id)

    assert approved.status == "approved"
    assert approved.approved_by_user_id == admin_user.id
    assert approved.approved_at is not None
    assert approved.published_at is not None


def test_reject_template(db_session: Session, test_user: User, test_area: Area):
    """Test rejecting a template sets status to rejected."""
    admin_user = User(
        email="admin@example.com",
        hashed_password="hash",
        is_admin=True,
        is_confirmed=True,
    )
    db_session.add(admin_user)
    db_session.commit()
    
    # Publish template
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="To Be Rejected",
        description="This template will be rejected by admin for quality reasons.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)
    
    # Reject
    rejected = reject_template(db_session, template.id, admin_user.id)
    
    assert rejected.status == "rejected"
    assert rejected.approved_by_user_id == admin_user.id


def test_get_template_by_id(db_session: Session, test_user: User, test_area: Area):
    """Test retrieving template by ID."""
    request = TemplatePublishRequest(
        area_id=test_area.id,
        title="Retrievable Template",
        description="This template can be retrieved by its unique identifier.",
        category="test",
        tags=["test"],
    )
    template = publish_template(db_session, test_user.id, request)
    
    # Retrieve
    retrieved = get_template_by_id(db_session, template.id)
    
    assert retrieved is not None
    assert retrieved.id == template.id
    assert retrieved.title == template.title


def test_get_template_by_id_not_found(db_session: Session):
    """Test retrieving non-existent template returns None."""
    fake_id = uuid.uuid4()
    result = get_template_by_id(db_session, fake_id)
    
    assert result is None
