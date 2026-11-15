"""Re-export of the fake wallet, which now lives in the app (dev backend)."""

from app.lightning.fake import FakeLightningWallet

__all__ = ["FakeLightningWallet"]
