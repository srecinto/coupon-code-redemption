import os
import config
import json
import time
import datetime
import csv
import io
import uuid

from functools import wraps
from flask import Flask, request, session, send_from_directory, redirect, make_response, render_template, Response
from flask_sslify import SSLify
from werkzeug import secure_filename
from email.utils import parseaddr
from utils.db import RedemptionCodeDB
from utils.rest import OktaUtil

"""
GLOBAL VARIABLES ########################################################################################################
"""
app = Flask(__name__)
app.debug = False
app.config.update({
    "SECRET_KEY": "6w_#w*~AVts3!*yd&C]jP0(x_1ssd]MVgzfAw8%fF+c@|ih0s1H&yZQC&-u~O[--"  # For the session
})
sslify = SSLify(app, permanent=True, subdomains=True)


"""
UTILS ###################################################################################################################
"""


def authorized(f):
    @wraps(f)
    def decorated_function(*args, **kws):
        """ Decorator fucntion to make endpoint authorization checks easier for scopes defined in Okta """
        print("authorized()")
        authorization_header = None
        has_access = False
        authorization_token = None
        okta_util = OktaUtil(request.headers)

        if "Authorization" in request.headers:
            authorization_header = request.headers["Authorization"]
            authorization_token = authorization_header.replace("Bearer ", "") # Just get the access toke for introspection
        elif request.cookies:
            authorization_token = request.cookies.get("token")

        if authorization_token:
            introspection_response = okta_util.introspect_oauth_token(authorization_token)
            print("introspection_response: {0}".format(json.dumps(introspection_response, indent=4, sort_keys=True)))
            if "active" in introspection_response:
                if introspection_response["active"]:
                    # Add scope checks here if you like
                    has_access = True

        # print "authorization_header: {0}".format(authorization_header)

        if has_access:
            return f(*args, **kws)
        else:
            session["nonce"] = str(uuid.uuid4())
            session["state"] = str(uuid.uuid4())
            response = make_response(redirect(okta_util.create_oidc_auth_code_url(state=session["state"], nonce=session["nonce"])))
            response.set_cookie('token', "")
            return response

    return decorated_function


def json_converter(o):
    if isinstance(o, datetime.datetime):
        return o.__str__()


def validate_not_null(json, response, name, has_validation_error):
    print("validate_not_null()")
    result_message = ""

    if json[name] is None or json[name] == "":
        has_validation_error = True
        response["message"] += "\n{0} is required.".format(name)

    return has_validation_error


def validate_email(response, email, has_validation_error):
    print("validate_email()")

    if '@' not in parseaddr(email)[1]:
        has_validation_error = True
        response["message"] += "\nEmail is not properly formatted."

    return has_validation_error


def validate_redemption_code(response, redeemCode, has_validation_error):
    print("validate_redemption_code()")
    redemption_code_db = RedemptionCodeDB()
    redemption_code_record = redemption_code_db.get_redemption_code_by_code(redeemCode)

    # First check if it exsists then check that is had not been used already
    if(not redemption_code_record):
        has_validation_error = True
        response["message"] += "\nInvalid redemption code."
    else:
        print("redemption_code_record['email'] = {0}".format(redemption_code_record["email"]))
        if redemption_code_record["email"]: #If it has an email assume it was used
            has_validation_error = True
            response["message"] += "\nRedemption code has already been used."

    return has_validation_error, redemption_code_record


def map_redemption_code_record(request_json, redemption_code_record):
    print("map_redemption_code_record()")

    #print("redemption_code_record: {0}".format(json.dumps(redemption_code_record, indent=4, sort_keys=True, default=json_converter)))

    redemption_code_record["redeemCode"] = request_json["redeemCode"]
    redemption_code_record["firstName"] = request_json["firstName"]
    redemption_code_record["lastName"] = request_json["lastName"]
    redemption_code_record["address1"] = request_json["address1"]
    redemption_code_record["address2"] = request_json["address2"]
    redemption_code_record["city"] = request_json["city"]
    redemption_code_record["state"] = request_json["state"]
    redemption_code_record["postalCode"] = request_json["postalCode"]
    redemption_code_record["phone"] = request_json["phone"]
    redemption_code_record["email"] = request_json["email"]

    #print("redemption_code_record: {0}".format(json.dumps(redemption_code_record, indent=4, sort_keys=True, default=json_converter)))


def get_oauth_token(oauth_code):
    print("get_oauth_token()")
    okta_util = OktaUtil(request.headers)

    oauth_token_response_json = okta_util.get_oauth_token(oauth_code)
    print("oauth_token_response_json: {0}".format(json.dumps(oauth_token_response_json), indent=4, sort_keys=True))

    return oauth_token_response_json["access_token"]


"""
ROUTES ##################################################################################################################
"""


@app.route('/<path:filename>')
def serve_static_html(filename):
    """ serve_static_html() generic route function to serve files in the 'static' folder """
    root_dir = os.path.dirname(os.path.realpath(__file__))
    return send_from_directory(os.path.join(root_dir, 'static'), filename)


@app.route('/')
def index():
    """ handler for the root url path of the app """
    print("index()")
    message = ""

    response = make_response(render_template("index.html", app_config=config.app, message=message))

    return response


@app.route('/order-confirmation')
def order_confirmation():
    """ handler for the order confirmation url path of the app """
    print("order_confirmation()")
    message = ""

    response = make_response(render_template("order_confirmation.html", app_config=config.app, message=message))

    return response


@app.route('/redeemCode', methods=["POST"])
def redeem_code():
    """ handler for the redeeming the code of the app """
    print("redeem_code()")
    print("request.form: {0}".format(request.form))
    request_json = request.get_json()
    print("request.get_json(): {0}".format(request_json))

    has_validation_error = False

    response = {
        "status": "FAILED",
        "message": "Please correct the following: ",
        "request_json": request_json
    }

    # Validate Request
    has_validation_error = validate_not_null(request_json, response, "redeemCode", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "firstName", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "lastName", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "address1", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "city", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "state", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "phone", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "postalCode", has_validation_error)
    has_validation_error = validate_not_null(request_json, response, "email", has_validation_error)
    has_validation_error = validate_email(response, request_json["email"], has_validation_error)
    has_validation_error, redemption_code_record = validate_redemption_code(response, request_json["redeemCode"], has_validation_error)

    if not has_validation_error:
        redemption_code_db = RedemptionCodeDB()
        #print("redemption_code_record: {0}".format(json.dumps(redemption_code_record, indent=4, sort_keys=True, default=json_converter)))
        map_redemption_code_record(request_json, redemption_code_record)
        #print("redemption_code_record: {0}".format(json.dumps(redemption_code_record, indent=4, sort_keys=True, default=json_converter)))
        redemption_code_record_updated = redemption_code_db.update_redemption_code(redemption_code_record)

        print("redemption_code_record_updated: {0}".format(json.dumps(redemption_code_record_updated, indent=4, sort_keys=True, default=json_converter)))
        okta_util = OktaUtil(request.headers)
        recipients = [
            {
                "address": {
                    "email": request_json["email"],
                    "name": "{0} {1}".format(request_json["firstName"], request_json["lastName"])
                }
            }
        ]
        mail_response = okta_util.send_mail(os.environ["SPARKPOST_THANK_TEMPLATE_ID"], recipients)

        response["status"] = "SUCCESS"
        response["message"] = "Your request is being processed.  Please check your email for a status update."

    # else respond with error by default

    return json.dumps(response)


@app.route('/oidc', methods=["POST"])
def oidc():
    """ handler for the oidc call back of the app """
    print("oidc()")
    # print(request.form)

    if "error" in request.form:
        print("ERROR: {0}, MESSAGE: {1}".format(request.form["error"], request.form["error_description"]))

    # Check Nonce
    # print("state: '{0}'".format(session["state"]))
    # print("nonce: '{0}'".format(session["nonce"]))
    if session["state"] == request.form["state"]:
        oidc_code = request.form["code"]
        print("oidc_code: {0}".format(oidc_code))
        oauth_token = get_oauth_token(oidc_code)
        redirect_url = os.environ["APP_AUTH_URL"]
        response = make_response(redirect(redirect_url))
        response.set_cookie('token', oauth_token)
    else:
        print("FAILED TO MATCH STATE!!!")
        response = make_response(redirect(os.environ["APP_AUTH_URL"]))

    session.pop("state", None)
    session.pop("nonce", None)

    return response


@app.route('/admin')
@authorized
def admin():
    """ handler for the admmin url path of the app """
    print("admin()")
    message = ""

    response = make_response(render_template("admin.html", app_config=config.app, message=message))

    return response


@app.route('/admin/codefileupload', methods=["POST"])
@authorized
def code_file_upload():
    print("code_file_upload()")

    if "codeUploadFile" in request.files:
        message="Upload completed!"
        uploadedFile = request.files["codeUploadFile"]
        print("fileName: {0}".format(uploadedFile.filename))

        fileLocation = "{0}/{1}".format(config.app["temp_file_path"], secure_filename(uploadedFile.filename))
        print("fileLocation: {0}".format(fileLocation))

        uploadedFile.save(fileLocation)

        redemption_code_db = RedemptionCodeDB()

        arg_list = []
        duplicate_list = []

        with open(fileLocation, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0

            conn = redemption_code_db.get_connection()

            for row in csv_reader:
                print(row)
                # Check for duplicates

                dupeCheckRow = redemption_code_db.get_redemption_code_by_code(row["RedemptionCode"], conn)

                if dupeCheckRow:
                    print("Duplicate!  Handle it!")
                    duplicate_list.append(row["RedemptionCode"])
                    message="Upload completed! Duplicate codes detected."
                else:
                    arg_list.append([row["RedemptionCode"],row["ProductRef"]])

            if(len(duplicate_list) != 0):
                message="Upload completed! Duplicate codes detected. {0}".format(duplicate_list)

            redemption_code_db.commit_close_connection(conn)

        redemption_code_db.batch_create_redemption_code(arg_list)

    response = make_response(render_template("admin.html", app_config=config.app, message=message))

    return response


@app.route('/admin/trackingfileupload', methods=["POST"])
@authorized
def tracking_file_upload():
    print("trackingfileupload()")

    if "codeUploadFile" in request.files:
        message="Upload completed!"
        uploadedFile = request.files["codeUploadFile"]
        print("fileName: {0}".format(uploadedFile.filename))

        fileLocation = "{0}/{1}".format(config.app["temp_file_path"], secure_filename(uploadedFile.filename))
        print("fileLocation: {0}".format(fileLocation))

        uploadedFile.save(fileLocation)

        redemption_code_db = RedemptionCodeDB()

        with open(fileLocation, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                print(row)
                # Check for duplicates
                rowFound = redemption_code_db.get_redemption_code_by_code(row["RedemptionCode"])

                if rowFound:
                    print(updateTracking(row["RedemptionCode"], row["Tracking"]))
                else:
                    message="Upload completed! Some codes were missing."



    response = make_response(render_template("admin.html", app_config=config.app, message=message))

    return response


@app.route('/admin/availablecodestab')
@authorized
def available_codes_tab():
    """ handler for the admmin availablecodestab url path of the app """
    print("available_codes_tab()")
    redemption_code_db = RedemptionCodeDB()

    message = ""
    unused_codes = redemption_code_db.get_unused_redemption_codes()
    paging_info = {
        "total_rows": len(unused_codes)
    }

    response = make_response(
        render_template(
            "partTabAvailableCodes.html",
            app_config=config.app,
            message=message,
            unused_codes=unused_codes,
            paging_info=paging_info))

    return response


@app.route('/admin/pendingshippingtab')
@authorized
def pending_shipping_tab():
    """ handler for the admmin pendingshippingtab url path of the app """
    print("available_codes_tab()")
    redemption_code_db = RedemptionCodeDB()

    message = ""
    pending_shipping_items = redemption_code_db.get_pending_shipping_redemption_codes()
    paging_info = {
        "total_rows": len(pending_shipping_items)
    }

    response = make_response(
        render_template(
            "partTabPendingShipping.html",
            app_config=config.app,
            message=message,
            pending_shipping_items=pending_shipping_items,
            paging_info=paging_info))

    return response


@app.route('/admin/shippedtab')
@authorized
def shipped_tab():
    """ handler for the admmin shipped_tab url path of the app """
    print("shipped_tab()")
    redemption_code_db = RedemptionCodeDB()

    message = ""
    shipped_items = redemption_code_db.get_shipped_redemption_codes()
    paging_info = {
        "total_rows": len(shipped_items)
    }

    response = make_response(
        render_template(
            "partTabShipped.html",
            app_config=config.app,
            message=message,
            shipped_items=shipped_items,
            paging_info=paging_info))

    return response


@app.route('/admin/alltab')
@authorized
def all_tab():
    """ handler for the admmin all_tab url path of the app """
    print("all_tab()")
    redemption_code_db = RedemptionCodeDB()

    message = ""
    all_items = redemption_code_db.get_all_used_redemption_codes()
    paging_info = {
        "total_rows": len(all_items)
    }

    response = make_response(
        render_template(
            "partTabAll.html",
            app_config=config.app,
            message=message,
            all_items=all_items,
            paging_info=paging_info))

    return response


@app.route('/admin/exportall/<status>')
@authorized
def export_all(status=None):
    """ handler for the admmin export_all url path of the app """
    print("export_all()")
    redemption_code_db = RedemptionCodeDB()

    message = ""
    all_items = None
    if status == "pending":
        all_items = redemption_code_db.get_pending_shipping_redemption_codes()
    elif status == "shipped":
        all_items = redemption_code_db.get_shipped_redemption_codes()
    else:
        all_items = redemption_code_db.get_all_used_redemption_codes()

    #prep csv conversion for output
    csv_data_io = io.StringIO()
    csv_columns = [
        "productRef",
        "redeemCode",
        "firstName",
        "lastName",
        "address1",
        "address2",
        "city",
        "state",
        "postalCode",
        "phone",
        "email",
        "tracking",
        "created",
        "updated",
        "status"
    ]
    cw = csv.DictWriter(csv_data_io, fieldnames=csv_columns, dialect='excel')
    cw.writeheader()
    row_count = 0
    for item in all_items:
        cw.writerow(item)

    response = Response(
        csv_data_io.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=export.csv"})

    return response


@app.route('/admin/updateTracking/<redeem_code>/<tracking>', methods=["POST"])
@authorized
def updateTracking(redeem_code, tracking):
    """ handler for the redeeming the code of the app """
    print("updateTracking()")
    has_validation_error =  False

    response = {
        "status": "FAILED",
        "message": "Failed to update the tracking number: {0} for: {1}".format(tracking, redeem_code)
    }

    if redeem_code is None or redeem_code == "":
        has_validation_error = True

    if tracking is None or tracking == "":
        has_validation_error = True

    if not has_validation_error:
        redemption_code_db = RedemptionCodeDB()
        redemption_code_record = redemption_code_db.get_redemption_code_by_code(redeem_code)
        redemption_code_record["tracking"] = tracking
        redemption_code_record_updated = redemption_code_db.update_redemption_code(redemption_code_record)
        print("redemption_code_record_updated: {0}".format(json.dumps(redemption_code_record_updated, indent=4, sort_keys=True, default=json_converter)))

        okta_util = OktaUtil(request.headers)
        recipients = [
            {
                "address": {
                    "email": redemption_code_record["email"],
                    "name": "{0} {1}".format(redemption_code_record["firstName"], redemption_code_record["lastName"])
                }
            }
        ]
        substitution = {
            "tracking": tracking
        }
        mail_response = okta_util.send_mail(os.environ["SPARKPOST_TRACK_TEMPLATE_ID"], recipients, substitution)

        response["status"] = "SUCCESS"
        response["message"] = "Updated successfully!"

    return json.dumps(response)

"""
MAIN ##################################################################################################################
"""
if __name__ == "__main__":
    # This is to run on c9.io.. you may need to change or make your own runner
    print( "config.app: {0}".format(json.dumps(config.app, indent=4, sort_keys=True, default=json_converter)) )
    app.run(host=os.getenv("IP", "0.0.0.0"), port=int(os.getenv("PORT", 8080)))