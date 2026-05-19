import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "").strip()
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "").strip()
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    UNLOCK_PRICE_CENTS: int = int(os.getenv("UNLOCK_PRICE_CENTS", "2900"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]
    MAX_PAGES_PER_SITE: int = int(os.getenv("MAX_PAGES_PER_SITE", "8"))
    PAGE_TIMEOUT_MS: int = int(os.getenv("PAGE_TIMEOUT_MS", "20000"))

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)


settings = Settings()
