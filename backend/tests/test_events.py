def test_create_and_list_event(client, event):
    assert event["slug"] == "testcon"
    assert event["timezone"] == "America/Chicago"
    assert [e["slug"] for e in client.get("/admin/events").json()] == ["testcon"]


def test_duplicate_slug_is_rejected(client, event):
    again = client.post("/admin/events", json={
        "slug": "testcon", "name": "Again",
        "starts_at": "2027-04-16T08:00:00-05:00", "ends_at": "2027-04-16T17:00:00-05:00"})
    assert again.status_code == 409


def test_event_must_end_after_it_starts(client):
    bad = client.post("/admin/events", json={
        "slug": "backwards", "name": "Backwards",
        "starts_at": "2027-04-16T17:00:00-05:00", "ends_at": "2027-04-16T08:00:00-05:00"})
    assert bad.status_code == 422


def test_times_must_include_a_time_zone(client):
    bad = client.post("/admin/events", json={
        "slug": "no-tz", "name": "No TZ",
        "starts_at": "2027-04-16T08:00:00", "ends_at": "2027-04-16T17:00:00"})
    assert bad.status_code == 422
