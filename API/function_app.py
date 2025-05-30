import azure.functions as func

from WrapperFunction import api as fastapi_api

app = func.AsgiFunctionApp(app=fastapi_api, http_auth_level=func.AuthLevel.ANONYMOUS)