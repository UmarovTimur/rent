import uvicorn
from dotenv import load_dotenv

from src.settings.uvicorn import UvicornSettings

if __name__ == "__main__":
    load_dotenv()
    settings = UvicornSettings()
    uvicorn.run(
        "src.server.app:create_application",
        **settings.model_dump(),
    )
