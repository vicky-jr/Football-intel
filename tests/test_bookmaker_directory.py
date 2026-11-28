from app.providers.bookmaker_directory import BookmakerDirectory, BookmakerProfile


def test_seed_directory_contains_global_discovery_candidates_not_live_claims():
    directory = BookmakerDirectory()
    items = directory.list_profiles()
    assert len(items) >= 20
    assert any(item["operator_id"] == "draftkings" for item in items)
    assert any(item["operator_id"] == "sportybet" for item in items)
    assert all(item["integration_status"] == "not_connected" for item in items)
    assert all(item["verification_status"] == "not_verified" for item in items)
    assert all(item["supported_regions"] == () for item in items)


def test_directory_search_matches_aliases_and_display_names():
    directory = BookmakerDirectory()
    assert directory.list_profiles(query="888 sport")[0]["operator_id"] == "888sport"
    assert directory.list_profiles(query="Draft")[0]["display_name"] == "DraftKings"


def test_directory_registers_new_operator_and_normalizes_id_and_regions():
    directory = BookmakerDirectory(profiles=[])
    directory.register(BookmakerProfile(
        operator_id="NewBook",
        display_name="New Book",
        supported_regions=("gb", "ng"),
        integration_status="access_review",
    ))
    profile = directory.get("newbook")
    assert profile.supported_regions == ("GB", "NG")
    assert profile.integration_status == "access_review"


def test_directory_rejects_duplicate_ids_and_unknown_status():
    directory = BookmakerDirectory()
    try:
        directory.register(BookmakerProfile("1xbet", "Duplicate"))
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate operator ID should be rejected")

    try:
        BookmakerDirectory([BookmakerProfile(
            "bad", "Bad", integration_status="live_everywhere"
        )])
    except ValueError as exc:
        assert "integration_status" in str(exc)
    else:
        raise AssertionError("unsupported status should be rejected")


def test_directory_unknown_operator_raises_clear_error():
    directory = BookmakerDirectory()
    try:
        directory.get("not-a-real-operator")
    except KeyError as exc:
        assert "not in the discovery directory" in str(exc)
    else:
        raise AssertionError("unknown operator should raise")
