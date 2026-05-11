import uvicorn
from dotenv import load_dotenv

from src.server.app import create_application
from src.settings.uvicorn import UvicornSettings

if __name__ == "__main__":
    load_dotenv()
    settings = UvicornSettings()
    app_import = "src.server.app:create_application" if (settings.reload or settings.workers > 1) else create_application
    uvicorn.run(
        app_import,
        **settings.model_dump(),
    )
