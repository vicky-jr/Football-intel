from app.providers.bookmaker_directory import (
    BookmakerDirectory,
    BookmakerProfile,
)


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


def test_source_identity_link_starts_as_candidate_and_requires_evidence_to_verify():
    directory = BookmakerDirectory()
    directory.add_source_link("1xbet", "Sportradar", "book-123", "1X Bet")
    link = directory.list_source_links("1xBet")[0]
    assert link["provider_id"] == "sportradar"
    assert link["source_book_id"] == "book-123"
    assert link["verification_status"] == "candidate"

    try:
        directory.set_source_link_status(
            "1xbet", "sportradar", "book-123", "verified"
        )
    except ValueError as exc:
        assert "require evidence_url and last_checked_at" in str(exc)
    else:
        raise AssertionError("a link must not be verified without evidence")


def test_source_identity_link_can_be_verified_with_auditable_evidence():
    directory = BookmakerDirectory()
    directory.add_source_link("bet365", "sportradar", "sr-42", "bet365")
    directory.set_source_link_status(
        "bet365", "sportradar", "sr-42", "verified",
        evidence_url="https://example.org/provider-book-evidence",
        last_checked_at="2026-11-28T12:30:00Z",
        notes="Provider book identity matched against official operator evidence.",
    )
    link = directory.list_source_links("bet365")[0]
    assert link["verification_status"] == "verified"
    assert link["last_checked_at"] == "2026-11-28T12:30:00Z"
    assert directory.summary()["verified_source_identity_links"] == 1


def test_sqlite_source_identity_links_persist_and_require_known_operator(tmp_path):
    database = tmp_path / "source-links.sqlite3"
    first = BookmakerDirectory(database_path=database)
    first.add_source_link("sportybet", "datafeed-a", "id-987", "SPORTYBET")
    first.set_source_link_status(
        "sportybet", "datafeed-a", "id-987", "verified",
        evidence_url="https://example.org/source-match",
        last_checked_at="2026-11-28T13:00:00Z",
    )

    second = BookmakerDirectory(database_path=database)
    link = second.list_source_links("sportybet")[0]
    assert link["verification_status"] == "verified"
    assert link["source_book_name"] == "SPORTYBET"

    try:
        second.add_source_link("unknown-operator", "datafeed-a", "x", "Unknown")
    except KeyError as exc:
        assert "not in the discovery directory" in str(exc)
    else:
        raise AssertionError("source links must reference a known directory operator")


def test_source_identity_link_rejects_duplicate_and_invalid_evidence_url():
    directory = BookmakerDirectory()
    directory.add_source_link("1xbet", "feed-x", "same-id", "1xBet")
    try:
        directory.add_source_link("1xbet", "feed-x", "same-id", "1xBet")
    except ValueError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("duplicate source identity link should be rejected")

    try:
        directory.set_source_link_status(
            "1xbet", "feed-x", "same-id", "verified",
            evidence_url="not-a-url",
            last_checked_at="2026-11-28T13:00:00Z",
        )
    except ValueError as exc:
        assert "HTTP(S) URL" in str(exc)
    else:
        raise AssertionError("verified evidence must have a valid URL")


def test_source_identity_suggestions_only_use_exact_normalized_names():
    directory = BookmakerDirectory(profiles=[
        BookmakerProfile("bet365", "bet365"),
        BookmakerProfile("sportybet", "SportyBet", aliases=("sporty bet",)),
        BookmakerProfile("1xbet", "1xBet"),
    ])
    suggestions = directory.suggest_source_identity_matches([
        {"provider": "feed-x", "source_id": "id-1", "name": "BET 365"},
        {"provider": "feed-x", "source_id": "id-2", "name": "Sporty Bet"},
        {"provider": "feed-x", "source_id": "id-3", "name": "1xBet Official"},
        {"provider": "feed-x", "source_id": "id-4", "name": "Unknown Operator"},
    ])
    assert suggestions[0]["candidate_operator_ids"] == ["bet365"]
    assert suggestions[0]["suggestion_status"] == "exact_name_candidate"
    assert suggestions[1]["candidate_operator_ids"] == ["sportybet"]
    assert suggestions[1]["suggestion_status"] == "exact_name_candidate"
    assert suggestions[2]["suggestion_status"] == "unmatched"
    assert suggestions[3]["suggestion_status"] == "unmatched"
    assert all(item["review_required"] for item in suggestions)
    assert directory.list_source_links() == []


def test_source_identity_suggestions_flag_ambiguous_names():
    directory = BookmakerDirectory(profiles=[
        BookmakerProfile("brand-one", "Brand One", aliases=("shared name",)),
        BookmakerProfile("brand-two", "Brand Two", aliases=("shared name",)),
    ])
    suggestion = directory.suggest_source_identity_matches([
        {"provider": "feed-x", "source_id": "amb-1", "name": "Shared Name"},
    ])[0]
    assert suggestion["suggestion_status"] == "ambiguous"
    assert suggestion["candidate_operator_ids"] == ["brand-one", "brand-two"]


def test_bookmaker_coverage_api_counts_only_verified_source_links(monkeypatch):
    from app.api import bookmakers as bookmaker_api

    directory = BookmakerDirectory(profiles=[
        BookmakerProfile("example-book", "Example Book"),
    ])
    directory.add_source_link("example-book", "feed-a", "verified-id", "Example")
    directory.set_source_link_status(
        "example-book", "feed-a", "verified-id", "verified",
        evidence_url="https://example.org/identity-proof",
        last_checked_at="2026-11-28T14:00:00Z",
    )
    directory.add_source_link("example-book", "feed-b", "candidate-id", "Example New")
    directory.add_source_link("example-book", "feed-c", "rejected-id", "Wrong Match")
    directory.set_source_link_status("example-book", "feed-c", "rejected-id", "rejected")

    class FakeMarketStore:
        def source_book_coverage_report(self, provider=None):
            self.requested_providers = getattr(self, "requested_providers", [])
            self.requested_providers.append(provider)
            return {
                "source_books": [
                    {
                        "provider_id": "feed-a",
                        "source_book_id": "verified-id",
                        "market_observations": 12,
                    },
                    {
                        "provider_id": "feed-b",
                        "source_book_id": "candidate-id",
                        "market_observations": 99,
                    },
                ]
            }

    monkeypatch.setattr(bookmaker_api, "bookmaker_directory", directory)
    fake_store = FakeMarketStore()
    monkeypatch.setattr(bookmaker_api, "_market_store", fake_store)
    response = bookmaker_api.get_bookmaker_coverage("example-book")

    assert response["coverage_state"] == "observations_found"
    assert len(response["observed_market_coverage"]) == 1
    assert response["observed_market_coverage"][0]["provider_id"] == "feed-a"
    assert len(response["candidate_source_links_not_counted"]) == 1
    assert len(response["rejected_source_links"]) == 1
    assert fake_store.requested_providers == ["feed-a"]


def test_suggested_identity_endpoint_reads_provider_books_without_auto_linking(monkeypatch):
    from app.api import bookmakers as bookmaker_api

    directory = BookmakerDirectory(profiles=[
        BookmakerProfile("sportybet", "SportyBet", aliases=("sporty bet",)),
    ])

    class FakeMarketStore:
        def discovery_inventory(self, provider=None, stage=None, limit=None):
            assert provider == "feed-a"
            assert stage == "books"
            return [
                {
                    "provider": "feed-a", "source_id": "sb-1",
                    "name": "SPORTY BET", "captured_at": "2026-11-28T15:00:00Z",
                },
                {
                    "provider": "feed-a", "source_id": "unknown-1",
                    "name": "Unlisted Operator", "captured_at": "2026-11-28T15:00:00Z",
                },
            ]

    monkeypatch.setattr(bookmaker_api, "bookmaker_directory", directory)
    monkeypatch.setattr(bookmaker_api, "_market_store", FakeMarketStore())
    response = bookmaker_api.suggested_bookmaker_source_links(
        provider_id="feed-a", limit=100
    )

    assert response["source_books_considered"] == 2
    assert response["suggestion_counts"] == {
        "exact_name_candidate": 1, "unmatched": 1,
    }
    assert directory.list_source_links() == []



def test_sqlite_audit_log_records_operator_and_source_link_decisions(tmp_path):
    import sqlite3

    database = tmp_path / "bookmaker-audit.sqlite3"
    directory = BookmakerDirectory(database_path=database)
    directory.update(
        BookmakerProfile(
            operator_id="1xbet",
            display_name="1xBet",
            integration_status="access_review",
            verification_status="partially_verified",
            notes="Access review is underway.",
            access_method="official_api",
            terms_review_status="in_review",
            evidence_url="https://evidence.example/operator?access_token=not-for-audit",
            last_checked_at="2026-11-28T12:00:00Z",
        ),
        actor_id="reviewer-17",
        reason="Started documented access and terms review",
    )
    directory.add_source_link(
        "1xbet", "feed-a", "book-77", "1X Bet",
        actor_id="reviewer-17",
        reason="Feed catalogue identity requires review",
    )
    directory.set_source_link_status(
        "1xbet", "feed-a", "book-77", "verified",
        evidence_url="https://evidence.example/match?token=private",
        last_checked_at="2026-11-28T12:30:00Z",
        notes="Matched using official operator evidence.",
        actor_id="reviewer-18",
        reason="Official operator evidence confirmed this provider identity",
    )

    history = directory.audit_history(limit=10)
    assert [item["action"] for item in history[:3]] == [
        "source_link.verified", "source_link.created", "operator.updated"
    ]
    verification = history[0]
    assert verification["actor_id"] == "reviewer-18"
    assert verification["before"]["verification_status"] == "candidate"
    assert verification["after"]["verification_status"] == "verified"
    assert verification["evidence_url"] == "https://evidence.example/match"
    assert "private" not in verification["evidence_url"]
    assert history[2]["after"]["verification_status"] == "partially_verified"
    assert history[2]["evidence_url"] == "https://evidence.example/operator"

    filtered = directory.audit_history(
        entity_type="source_link",
        entity_id="1xbet:feed-a:book-77",
    )
    assert len(filtered) == 2
    integrity = directory.audit_integrity_report()
    assert integrity["verified"] is True
    assert integrity["entry_count"] == 3


def test_sqlite_audit_log_is_append_only_and_detects_hash_chain_tampering(tmp_path):
    import sqlite3

    database = tmp_path / "bookmaker-audit-immutable.sqlite3"
    directory = BookmakerDirectory(database_path=database)
    directory.add_source_link(
        "bet365", "feed-a", "source-1", "bet365",
        actor_id="reviewer-1",
    )
    event = directory.audit_history(limit=1)[0]

    connection = sqlite3.connect(database)
    try:
        try:
            connection.execute(
                "UPDATE bookmaker_audit_log SET reason = ? WHERE audit_id = ?",
                ("rewritten", event["audit_id"]),
            )
            connection.commit()
        except sqlite3.DatabaseError as exc:
            assert "append-only" in str(exc)
            connection.rollback()
        else:
            raise AssertionError("audit log updates must be rejected")
        try:
            connection.execute(
                "DELETE FROM bookmaker_audit_log WHERE audit_id = ?",
                (event["audit_id"],),
            )
            connection.commit()
        except sqlite3.DatabaseError as exc:
            assert "append-only" in str(exc)
            connection.rollback()
        else:
            raise AssertionError("audit log deletes must be rejected")
    finally:
        connection.close()

    assert directory.audit_integrity_report()["verified"] is True


def test_failed_source_verification_does_not_create_a_verification_audit_event(tmp_path):
    directory = BookmakerDirectory(database_path=tmp_path / "audit-validation.sqlite3")
    directory.add_source_link(
        "sportybet", "feed-a", "source-42", "SportyBet",
        actor_id="reviewer-1",
    )
    before = len(directory.audit_history())
    try:
        directory.set_source_link_status(
            "sportybet", "feed-a", "source-42", "verified",
            evidence_url="not-a-valid-url",
            last_checked_at="2026-11-28T12:00:00Z",
            actor_id="reviewer-2",
        )
    except ValueError as exc:
        assert "HTTP(S) URL" in str(exc)
    else:
        raise AssertionError("invalid verification evidence must be rejected")
    assert len(directory.audit_history()) == before


def test_audit_history_requires_persistent_storage_and_valid_limits():
    import pytest

    with pytest.raises(RuntimeError):
        BookmakerDirectory().audit_history()
    directory = BookmakerDirectory(database_path=":memory:")
    with pytest.raises(RuntimeError):
        directory.audit_integrity_report()
