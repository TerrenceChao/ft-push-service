from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from ..routers.res.response import res_err
import logging as log

log.basicConfig(filemode='w', level=log.INFO)

class NotFoundError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class UserError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
    
class BusinessError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class ErrorLogger:
    def __init__(self, msg: str):
        log.error(msg)
        

class ClientException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '40000'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_400_BAD_REQUEST
        
    def __str__(self):
        return self.msg
        
class UnauthorizedException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '40100'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_401_UNAUTHORIZED
        
    def __str__(self):
        return self.msg

class ForbiddenException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '40300'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_403_FORBIDDEN
        
    def __str__(self):
        return self.msg

class NotFoundException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '40400'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_404_NOT_FOUND
        
    def __str__(self):
        return self.msg
        
class NotAcceptableException(HTTPException, ErrorLogger):
    def __init__(self, msg: str):
        self.msg = msg
        self.status_code = status.HTTP_406_NOT_ACCEPTABLE
        
    def __str__(self):
        return self.msg

class DuplicateUserException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '40600'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_406_NOT_ACCEPTABLE
        
    def __str__(self):
        return self.msg
        
class ServerException(HTTPException, ErrorLogger):
    def __init__(self, msg: str, code: str = '50000'):
        self.msg = msg
        self.code = code
        self.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
    def __str__(self):
        return self.msg


def __client_exception_handler(request: Request, exc: ClientException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))

def __unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))

def __forbidden_exception_handler(request: Request, exc: ForbiddenException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))

def __not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))

def __not_acceptable_exception_handler(request: Request, exc: NotAcceptableException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg))

def __duplicate_user_exception_handler(request: Request, exc: DuplicateUserException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))

def __server_exception_handler(request: Request, exc: ServerException):
    return JSONResponse(status_code=exc.status_code, content=res_err(msg=exc.msg, code=exc.code))




def include_app(app: FastAPI):
    app.add_exception_handler(ClientException, __client_exception_handler)
    app.add_exception_handler(UnauthorizedException, __unauthorized_exception_handler)
    app.add_exception_handler(ForbiddenException, __forbidden_exception_handler)
    app.add_exception_handler(NotFoundException, __not_found_exception_handler)
    app.add_exception_handler(NotAcceptableException, __not_acceptable_exception_handler)
    app.add_exception_handler(DuplicateUserException, __duplicate_user_exception_handler)
    app.add_exception_handler(ServerException, __server_exception_handler)
