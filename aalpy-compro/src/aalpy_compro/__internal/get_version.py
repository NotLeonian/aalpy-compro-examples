from importlib.metadata import PackageNotFoundError, version as dist_version

from .names import DIST_NAME


def get_version() -> str:
    """
    この aalpy-compro のバージョンを取得して返す
    """

    try:
        return dist_version(DIST_NAME)
    except PackageNotFoundError:
        # fallback-version
        # 例外は送出しない
        return "0.0.0 (fallback)"
