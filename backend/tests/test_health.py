from app import create_app, db


def test_health_endpoint():
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    client = app.test_client()
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "application": "PayPilot AI",
        "status": "operational",
        "version": "1.0.0",
    }
