"""Google Earth Engine connection.

Initializes once per process and is reused by any module that needs to
query Earth Engine datasets (Copernicus DEM, JRC Global Surface Water).
"""

from functools import lru_cache

import ee

from app.config import settings


@lru_cache(maxsize=1)
def get_ee_client() -> ee:
    credentials = ee.ServiceAccountCredentials(
        settings.GEE_SERVICE_ACCOUNT_EMAIL, settings.GEE_KEY_PATH
    )
    ee.Initialize(credentials, project=settings.GEE_PROJECT_ID)
    return ee
