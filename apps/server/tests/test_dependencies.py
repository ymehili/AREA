from app.api.dependencies.auth import require_active_user


def test_require_active_user_noop():
    # The dependency currently only ensures the dependency chain runs without errors.
    assert require_active_user() is None
