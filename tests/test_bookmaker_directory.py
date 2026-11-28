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
    assert directory.list_profiles(query="paripesa")[0]["operator_id"] == "paripesa"


def test_directory_registers_new_operator_and_normalizes_id_and_regions():
    directory = BookmakerDirectory(profiles=[])
    directory.register(BookmakerProfile(
        operator_id="NewBook",
        display_name="New Book",
        supported_regions=("gb", "ng", "GB"),
        integration_status="access_review",
        terms_review_status="in_review",
    ))
    profile = directory.get("newbook")
    assert profile.supported_regions == ("GB", "NG")
    assert profile.integration_status == "access_review"
    assert profile.terms_review_status == "in_review"


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


def test_sqlite_directory_persists_records_and_updates_between_instances(tmp_path):
    database = tmp_path / "bookmakers.sqlite3"
    first = BookmakerDirectory(database_path=database)
    assert len(first.list_profiles()) >= 20

    first.update(BookmakerProfile(
        operator_id="1xbet",
        display_name="1xBet",
        aliases=("1xbet",),
        integration_status="access_review",
        verification_status="partially_verified",
        supported_regions=("ng", "gb"),
        notes="Access review started; no live integration claimed.",
        access_method="official_api",
        terms_review_status="in_review",
        evidence_url="https://example.org/evidence",
        last_checked_at="2026-11-28T12:00:00Z",
    ))

    second = BookmakerDirectory(database_path=database)
    profile = second.get("1xbet")
    assert profile.integration_status == "access_review"
    assert profile.verification_status == "partially_verified"
    assert profile.supported_regions == ("GB", "NG")
    assert profile.access_method == "official_api"
    assert profile.evidence_url == "https://example.org/evidence"


def test_sqlite_directory_preserves_operator_updates_when_seeded_again(tmp_path):
    database = tmp_path / "bookmakers.sqlite3"
    first = BookmakerDirectory(database_path=database)
    first.update(BookmakerProfile(
        operator_id="sportybet",
        display_name="SportyBet",
        integration_status="connected",
        verification_status="not_verified",
        notes="Connection configured; ingestion not verified.",
    ))

    # Application restart should not reset a real status to the seed defaults.
    second = BookmakerDirectory(database_path=database)
    assert second.get("sportybet").integration_status == "connected"


def test_directory_summary_and_region_filter_only_report_recorded_regions():
    directory = BookmakerDirectory(profiles=[
        BookmakerProfile(
            "example-ng", "Example NG", supported_regions=("ng",),
            integration_status="ingestion_verified", verification_status="verified",
        ),
        BookmakerProfile("example-uk", "Example UK", supported_regions=("gb",)),
    ])
    assert [x["operator_id"] for x in directory.list_profiles(region="ng")] == ["example-ng"]
    assert directory.summary()["live_ingestion_verified"] == 1
    assert directory.summary()["regions_with_recorded_support"] == ["GB", "NG"]
