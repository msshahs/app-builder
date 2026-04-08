import os
from pymongo import MongoClient
from core.utils import get_logger

logger = get_logger("mongodb")


def provision_app_database(project_id: str) -> dict:
    """
    Create a new database for a generated app.
    Returns connection details for injection into .env
    """
    atlas_uri = os.getenv("MONGODB_ATLAS_URI")
    db_prefix = os.getenv("MONGODB_ATLAS_DB_PREFIX", "app_builder")

    if not atlas_uri:
        raise ValueError("MONGODB_ATLAS_URI not set in .env")

    db_name = f"{db_prefix}_{project_id}"

    logger.info(f"Provisioning database: {db_name}")

    # Connect to Atlas and create the database
    # MongoDB creates databases lazily — we create a collection to initialize it
    client = MongoClient(atlas_uri)
    db = client[db_name]

    # Create a metadata collection to initialize the database
    db["_metadata"].insert_one({
        "project_id": project_id,
        "created_at": __import__("datetime").datetime.utcnow(),
        "status": "active"
    })

    client.close()

    # Build the connection string for this specific database
    # Insert the database name before the query params
    base_uri = atlas_uri.split("?")[0].rstrip("/")
    app_mongo_uri = f"{base_uri}/{db_name}?retryWrites=true&w=majority"

    logger.info(f"Database provisioned: {db_name}")

    return {
        "db_name": db_name,
        "mongo_uri": app_mongo_uri
    }


def deprovision_app_database(project_id: str):
    """Drop a database when an app is deleted."""
    atlas_uri = os.getenv("MONGODB_ATLAS_URI")
    db_prefix = os.getenv("MONGODB_ATLAS_DB_PREFIX", "app_builder")
    db_name = f"{db_prefix}_{project_id}"

    client = MongoClient(atlas_uri)
    client.drop_database(db_name)
    client.close()

    logger.info(f"Database dropped: {db_name}")