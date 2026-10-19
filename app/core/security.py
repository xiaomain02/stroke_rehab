"""Authentication and authorization dependency stubs."""


def get_current_user():
    ...


def require_roles(*roles: str):
    ...


def assert_patient_access(patient_id: int, current_user) -> None:
    ...
