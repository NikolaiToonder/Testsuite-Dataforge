def test_dump_routes(client):
    """Debug function to print out all routes known to FastAPI"""
    print("\n\n=== REGISTERED ROUTES ===")
    for route in client.app.routes:
        if hasattr(route, "path"):
            print(f"{list(route.methods)} {route.path}")
    print("=========================\n")