import os
import requests
import base64
import json

# from requests.packages.urllib3.exceptions import InsecurePlatformWarning
# from requests.packages.urllib3.exceptions import SNIMissingWarning


class OktaUtil:
    # TODO: This should be configuration driven
    REST_HOST = None
    REST_TOKEN = None
    OKTA_SESSION_ID_KEY = "okta_session_id"
    OKTA_SESSION_TOKEN_KEY = "okta_session_id"
    DEVICE_TOKEN = None
    OKTA_HEADERS = {}
    OKTA_OAUTH_HEADERS = {}
    OIDC_CLIENT_ID = None
    OIDC_CLIENT_SECRET = None
    AUTH_SERVER_ID = None

    def __init__(self, headers):
        # This is to supress the warnings for the older version
        # requests.packages.urllib3.disable_warnings((InsecurePlatformWarning, SNIMissingWarning))

        self.REST_HOST = os.environ["OKTA_ORG_URL"]
        self.REST_TOKEN = os.environ["OKTA_API_TOKEN"]
        self.OIDC_CLIENT_ID = os.environ["OKTA_APP_CLIENT_ID"]
        self.OIDC_CLIENT_SECRET = os.environ["OKTA_APP_CLIENT_SECRET"]
        self.OIDC_REDIRECT_URL = os.environ["OKTA_OIDC_REDIRECT_URL"]
        if "OKTA_AUTHSERVER_ID" in os.environ:
            self.AUTH_SERVER_ID = os.environ["OKTA_AUTHSERVER_ID"]
            print("HAS AUTH SERVER: {0}".format(self.AUTH_SERVER_ID))

        user_agent = ""
        if "User-Agent" in headers:
            user_agent = headers["User-Agent"]



        self.OKTA_HEADERS = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "SSWS {api_token}".format(api_token=self.REST_TOKEN),
            "User-Agent": user_agent
        }

        if "X-Forwarded-For" in headers:
            self.OKTA_HEADERS["X-Forwarded-For"] = headers["X-Forwarded-For"]

        if "X-Forwarded-Port" in headers:
            self.OKTA_HEADERS["X-Forwarded-Port"] = headers["X-Forwarded-Port"]

        if "X-Forwarded-Proto" in headers:
            self.OKTA_HEADERS["X-Forwarded-Proto"] = headers["X-Forwarded-Proto"]

        self.OKTA_OAUTH_HEADERS = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {encoded_auth}".format(
                encoded_auth=self.get_encoded_auth(
                    client_id=self.OIDC_CLIENT_ID,
                    client_secret=self.OIDC_CLIENT_SECRET))
        }

        print("OKTA_OAUTH_HEADERS: {0}".format(json.dumps(self.OKTA_OAUTH_HEADERS, indent=4, sort_keys=True)))


    def get_user(self, user_id):
        print("get_user()")
        url = "{host}/api/v1/users/{user_id}".format(host=self.REST_HOST, user_id=user_id)
        body = {}

        return self.execute_get(url, body)


    def update_user(self, user):
        print("update_user()")
        url = "{host}/api/v1/users/{user_id}".format(host=self.REST_HOST, user_id=user["id"])

        return self.execute_post(url, user)


    def userinfo_oauth(self, oauth_token):
        print("userinfo_oauth()")
        auth_server = ""

        if self.AUTH_SERVER_ID:
            auth_server = "/{0}".format(self.AUTH_SERVER_ID)

        url = "{host}/oauth2{auth_server}/v1/userinfo".format(
            host=self.REST_HOST,
            auth_server=auth_server)

        body = {}
        # print("oauth_token: ", oauth_token)
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer {0}".format(oauth_token)
        }

        return self.execute_get(url, body, headers)


    def introspect_oauth_token(self, oauth_token):
        print("introspect_oauth_token()")

        auth_server = ""

        if self.AUTH_SERVER_ID:
            auth_server = "/{0}".format(self.AUTH_SERVER_ID)

        url = "{host}/oauth2{auth_server}/v1/introspect?token={token}".format(
            host=self.REST_HOST,
            auth_server=auth_server,
            token=oauth_token)
        body = {}

        return self.execute_post(url, body, self.OKTA_OAUTH_HEADERS)


    def get_user_application_profile(self, app_id, user_id):
        print("get_user_application_profile()")
        url = "{host}/api/v1/apps/{app_id}/users/{user_id}".format(host=self.REST_HOST, app_id=app_id, user_id=user_id)
        body = {}
        return self.execute_get(url, body)


    def update_user_application_profile(self, app_id, user_id, user_app_profile):
        print("update_user_application_profile()")
        url = "{host}/api/v1/apps/{app_id}/users/{user_id}".format(host=self.REST_HOST, app_id=app_id, user_id=user_id)
        body = user_app_profile
        return self.execute_post(url, body)


    def execute_post(self, url, body, headers=None):
        print("execute_post(): ", url)
        print(body)

        headers = self.reconcile_headers(headers)

        rest_response = requests.post(url, headers=headers, json=body)
        response_json = rest_response.json()

        # print json.dumps(response_json, indent=4, sort_keys=True)
        return response_json

    def execute_put(self, url, body, headers=None):
        print("execute_put(): ", url)
        print(body)

        headers = self.reconcile_headers(headers)

        rest_response = requests.put(url, headers=headers, json=body)
        response_json = rest_response.json()

        # print json.dumps(response_json, indent=4, sort_keys=True)
        return response_json

    def execute_delete(self, url, body, headers=None):
        print("execute_delete(): ", url)
        print(body)

        headers = self.reconcile_headers(headers)

        rest_response = requests.delete(url, headers=headers, json=body)
        try:
            response_json = rest_response.json()
        except:
            response_json = {"status": "none"}

        # print json.dumps(response_json, indent=4, sort_keys=True)
        return response_json

    def execute_get(self, url, body, headers=None):
        print("execute_get(): ", url)
        print(body)

        headers = self.reconcile_headers(headers)

        rest_response = requests.get(url, headers=headers, json=body)
        response_json = rest_response.json()

        # print json.dumps(response_json, indent=4, sort_keys=True)
        return response_json

    def reconcile_headers(self, headers):

        if headers is None:
            headers = self.OKTA_HEADERS

        return headers

    def get_encoded_auth(self, client_id, client_secret):
        print("get_encoded_auth()")
        auth_raw = "{client_id}:{client_secret}".format(
            client_id=client_id,
            client_secret=client_secret
        )

        print("auth_raw: {0}".format(auth_raw))
        encoded_auth = base64.b64encode(bytes(auth_raw, 'UTF-8')).decode("UTF-8")
        print("encoded_auth: {0}".format(encoded_auth))

        return encoded_auth


    def create_oidc_auth_code_url(self, nonce, session_token=None):
        print("create_oidc_auth_code_url()")
        print("session_token: {0}".format(session_token))
        session_option = ""
        auth_server = ""

        if (session_token):
            session_option = "&sessionToken={session_token}".format(session_token=session_token)

        if self.AUTH_SERVER_ID:
            auth_server = "/{0}".format(self.AUTH_SERVER_ID)

        url = (
            "{host}/oauth2{auth_server}/v1/authorize?"
            "response_type=code&"
            "client_id={clint_id}&"
            "redirect_uri={redirect_uri}&"
            "state=hjasd-u832&"
            "nonce={nonce}&"
            "response_mode=form_post&"
            "prompt=none&"
            "scope=openid"
            "{session_option}"
        ).format(
            host=self.REST_HOST,
            auth_server=auth_server,
            clint_id=self.OIDC_CLIENT_ID,
            redirect_uri=self.OIDC_REDIRECT_URL,
            session_option=session_option,
            nonce=nonce
        )
        return url


    def get_oauth_token(self, oauth_code):
        print("get_oauth_token()")
        print("oauth_code: {0}".format(oauth_code))
        auth_server = ""

        if self.AUTH_SERVER_ID:
            auth_server = "/{0}".format(self.AUTH_SERVER_ID)

        url = (
            "{host}/oauth2{auth_server}/v1/token?"
            "grant_type=authorization_code&"
            "code={code}&"
            "redirect_uri={redirect_uri}"
        ).format(
            host=self.REST_HOST,
            auth_server=auth_server,
            code=oauth_code,
            redirect_uri=self.OIDC_REDIRECT_URL
        )

        body = {
            "authorization_code": oauth_code
        }

        return self.execute_post(url, body, self.OKTA_OAUTH_HEADERS)
