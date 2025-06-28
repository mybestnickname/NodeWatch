from http import HTTPStatus

from fastapi import HTTPException

InternalError = HTTPException(
    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
    detail='Internal error.',
)

UnprocessableEntityError = HTTPException(
    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
    detail='Unprocessable entity',
)
