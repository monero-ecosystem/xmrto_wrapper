#!/usr/bin/env python

"""
Goal:
  * Interact with XMR.to.

How to:
  * General usage
    - `python xmrto_wrapper.py create-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
    - `python xmrto_wrapper.py track-order --secret-key xmrto-ebmA9q`
    - `python xmrto_wrapper.py create-and-track-order --destination 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY --btc-amount 0.001`
    - `python xmrto_wrapper.py price --btc-amount 0.01`
    - `python xmrto_wrapper.py qrcode --data "something"`
  * Get help
    - xmrto_wrapper.py -h
  * You can
    - Create an order: `xmrto_wrapper.py create-order`
    - Track an order: `xmrto_wrapper.py track-order`
    - Get a recent price: `xmrto_wrapper.py price`
    - Create a QR code: `xmrto_wrapper.py qrcode`
  * The API used is `--api v2` by default, so no need to actually set that parameter.
  * The URL used is `--url https://xmr.to` by default, so no need to actually set that parameter.

Configuration:
  * The XMR.to url can be given as environemnt variable XMRTO_URL
    - `XMRTO_URL=https://xmr.to python xmrto_wrapper.py -d 3K1jSVxYqzqj7c9oLKXC7uJnwgACuTEZrY -b 0.001`
  * The XMR.to url can be given as argument (-u, --url)
    - python create_order.py --url <xmrto_url> --api <api_version> --destination <btc_address> --btc-amount <btc_amount>
  * If the BTC destination address is set both ways, BTC_ADDRESS has precedence.
  * The API version can be given as environemnt variable API_VERSION
  * The API version can be given as argument (-a, --api)
  * If the API version is set both ways, API_VERSION has precedence.
  * The BTC destination address can be given as environemnt variable BTC_ADDRESS
  * The BTC destination address can be given as argument (-d, --destination)
  * If the BTC destination address is set both ways, BTC_ADDRESS has precedence.
  * The BTC amount can be given as environemnt variable BTC_AMOUNT
  * The BTC amount can be given as argument (-b, --btc-amount)
  * If the BTC amount is set both ways, BTC_AMOUNT has precedence.
  * The XMR amount can be given as environemnt variable XMR_AMOUNT
  * The XMR amount can be given as argument (-x, --xmr-amount)
  * If the XMR amount is set both ways, XMR_AMOUNT has precedence.
  * It's possible to adda `--debug` flag. It produces additional log messages.
  * In some (special) cases it's necessary to use a local certificate.
    - `-- certificate "/usr/local/share/ca-certificates/ansible-base-ca.crt"`
"""

import os
import sys
import argparse
import logging
import json
import time
import collections
from typing import Dict

from requests import auth, Session, codes
from requests.exceptions import ConnectionError, SSLError


logging.basicConfig()
logger = logging.getLogger(__name__)

XMRTO_URL = os.environ.get("XMRTO_URL", None)
API_VERSION = os.environ.get("API_VERSION", None)
DESTINATION_ADDRESS = os.environ.get("BTC_ADDRESS", None)
PAY_AMOUNT = os.environ.get("BTC_AMOUNT", None)
XMR_AMOUNT = os.environ.get("XMR_AMOUNT", None)
CERTIFICATE = os.environ.get("XMRTO_CERTIFICATE", None)
QR_DATA = os.environ.get("QR_DATA", None)
SECRET_KEY = os.environ.get("SECRET_KEY", None)

parser = argparse.ArgumentParser(
    description="Create a XMR,.to order.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
# Same for all subcommnds
config = argparse.ArgumentParser(add_help=False)

config.add_argument(
    "-u",
    "--url",
    nargs="?",
    default="https://xmr.to",
    help="XMR.to url to use.",
)
config.add_argument("-a", "--api", default="v2", help="API version to use.")

config.add_argument(
    "--debug", action='store_true',  help="Show debug info."
)
config.add_argument("-c", "--certificate", nargs="?", help="Local certificate.")

# subparsers
subparsers = parser.add_subparsers(help='Order sub commands..', dest='subcommand')

# Create order
create = subparsers.add_parser('create-order', parents=[config], help="Create an order.")
create.add_argument(
    "-d", "--destination", required=True, help="Destination (BTC) address to send money to."
)
group = create.add_mutually_exclusive_group()
group.add_argument("-b", "--btc-amount", help="Amount to send in BTC.")
group.add_argument("-x", "--xmr-amount", help="Amount to send in XMR.")

# Track order
track = subparsers.add_parser('track-order', parents=[config], help="Track an order.")
track.add_argument(
    "--secret-key", required=True,  help="Existing secret key of an existing order."
)

# Create and track order
create = subparsers.add_parser('create-and-track-order', parents=[config], help="Create an order and track it.")
create.add_argument(
    "-d", "--destination", required=True, help="Destination (BTC) address to send money to."
)
group = create.add_mutually_exclusive_group()
group.add_argument("-b", "--btc-amount", help="Amount to send in BTC.")
group.add_argument("-x", "--xmr-amount", help="Amount to send in XMR.")

# Recent price
price = subparsers.add_parser('price', parents=[config], help="Get recent price.")
price.add_argument("-b", "--btc-amount", required=True, help="Amount to send in BTC.")

# Create qrcode
qrcode = subparsers.add_parser('qrcode', parents=[config], help="Create a qrcode, is stored in a file called 'qrcode.png'.")
qrcode.add_argument(
    "--data", required=True,  help="."
)

args = parser.parse_args()

DEBUG = args.debug
if DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

CREATE_ORDER = False
TRACK_ORDER = False
CREATE_AND_TRACK_ORDER = False
GET_PRICE = False
CREATE_QRCODE = False
if args.subcommand == "create-and-track-order":
    CREATE_AND_TRACK_ORDER = True
    if not DESTINATION_ADDRESS:
        DESTINATION_ADDRESS = args.destination
    
    if not PAY_AMOUNT:
        PAY_AMOUNT = args.btc_amount
    
    if not XMR_AMOUNT:
        XMR_AMOUNT = args.xmr_amount
if args.subcommand == "create-order":
    CREATE_ORDER = True
    if not DESTINATION_ADDRESS:
        DESTINATION_ADDRESS = args.destination
    
    if not PAY_AMOUNT:
        PAY_AMOUNT = args.btc_amount
    
    if not XMR_AMOUNT:
        XMR_AMOUNT = args.xmr_amount
elif args.subcommand == "track-order":
    TRACK_ORDER = True
    if not SECRET_KEY:
        SECRET_KEY = args.secret_key
elif args.subcommand == "price":
    GET_PRICE = True
    if not PAY_AMOUNT:
        PAY_AMOUNT = args.btc_amount
elif args.subcommand == "qrcode":
    CREATE_QRCODE = True
    if not QR_DATA:
        QR_DATA = args.data


if not XMRTO_URL:
    XMRTO_URL = args.url

if not API_VERSION:
    API_VERSION = args.api

if not CERTIFICATE:
    CERTIFICATE = args.certificate

# class Status():
#     def __init__(self, **fields):
#         self.state = fields["state"]
#         self.in_out_rate = fields["in_out_rate"]
#         self.payment_subaddress = fields.get("payment_subaddress", None)
#         self.payment_address = fields["payment_address"]
#         self.payment_integrated_address = fields.get("payment_integrated_address", None)
#         self.payment_id_long = fields.get("payment_id_long", None)
#         self.payment_id_short = fields.get("payment_id_short", None)
#         self.in_amount = fields["in_amount"]
#         self.in_amount_remaining = fields["in_amount_remaining"]
#         self.in_confirmations_remaining = fields["in_confirmations_remaining"]
# 
#     def __str__(self):
#         return str(type(self)) + ": "  + json.dumps(self.__dict__)

STATUS_FIELDS = [
    "state",
    "in_out_rate",
    "payment_subaddress",
    "payment_address",
    "payment_integrated_address",
    "payment_id_long",
    "payment_id_short",
    "in_amount",
    "in_amount_remaining",
    "in_confirmations_remaining",
]
Status = collections.namedtuple("Status", STATUS_FIELDS)
StatusClass = Status
ORDER_FIELDS = ("uuid", "state", "out_amount")
Order = collections.namedtuple("Order", ORDER_FIELDS)
PRICE_FIELDS = ("out_amount", "in_amount", "in_out_rate")
Price = collections.namedtuple("Price", PRICE_FIELDS)


class XmrtoConnection:
    USER_AGENT = "XmrtoProxy/0.1"
    HTTP_TIMEOUT = 30

    __conn = None

    def __init__(self, timeout:int=HTTP_TIMEOUT):
        self.__timeout = timeout
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
            # look at python-monerorpc to get TLD from URL
            # "Host": "xmr.to",
        }
        if not self.__conn:
            self.__conn = Session()
            self.__conn.headers = headers

    def get(self, url:str, expect_json=True):
        return self._request(url=url, func=self._get, expect_json=expect_json)

    def _get(self, url:str):
        return self.__conn.get(
                   url=url, timeout=self.__timeout
              )

    def post(self, url:str, postdata:Dict[str, str]):
        return self._request(url=url, func=self._post, postdata=postdata)

    def _post(self, url:str, postdata:str, **kwargs):
        logger.debug(postdata)
        logger.debug(f"Additional request arguments: {kwargs}")
        return self.__conn.post(
                   url=url, data=postdata, timeout=self.__timeout, **kwargs
               )

    def _request(self, url:str, func, postdata:Dict[str, str]=None, expect_json=True):
        """Makes the HTTP request

        """

        logger.debug(f"--> URL: {url}")

        response = None
        try:
            try:
                data = dict({"url": url})
                if postdata:
                    data["postdata"] = json.dumps(postdata)
                    
                response = func(**data)
            except (SSLError) as e:
                # Disable verification: verify=False
                # , cert=path_to_certificate
                # , verify=True
                logger.debug(
                    f"SSL certificate error, trying certificate: {CERTIFICATE}"
                )
                data["cert"] = (CERTIFICATE)
                data["verify"] = True

                response = func(**data)
        except (ConnectionError) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            print(json.dumps(error_msg))
            sys.exit(1)
        except (Exception) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            print(json.dumps(error_msg))
            sys.exit(1)

        response_ = None
        try:
            response_ = self._get_response(response=response, expect_json=expect_json)
        except (ValueError) as e:
            error_msg = dict({"error": str(e)})
            error_msg["url"] = url
            print(json.dumps(error_msg))
            sys.exit(1)

        if not response_:
            error_msg = dict({"error": "Could not evaluate response."})
            error_msg["url"] = url
            print(json.dumps(error_msg))
            sys.exit(1)
        elif isinstance(response_, dict) and (not response_.get("error", None) is None):
            error_msg = response_
            error_msg["url"] = url
            print(json.dumps(error_msg))
            sys.exit(1)

        return response_

    def _get_response(self, response, expect_json=True):
        """Evaluate HTTP request response

        :return: Either JSON response or response object in case of PNG (QRCode)
        """

        # Compare against None
        # Response with 400 status code returns True for not response
        if response == None:
            raise ValueError(
                {
                    "error": "No response.",
                    "message": f"Response is {response}.",
                }
            )

        if response.status_code not in [
            codes.ok,
            codes.created,
            codes.bad,
            codes.forbidden,
            codes.not_found,
        ]:
            raise ValueError(
                {
                    "error": "HTTP status code",
                    "message": "Received HTTP status code {}".format(
                        response.status_code
                    ),
                }
            )
        http_response = response.text
        if http_response is None:
            raise ValueError(
                {
                    "error": "Empty response",
                    "message": "Missing HTTP response from server",
                }
            )

        json_response = None
        try:
            json_response = json.loads(http_response)
        except (json.decoder.JSONDecodeError) as e:
            if expect_json:
                raise ValueError(
                    {
                        "error": "",
                        "message": f"'{http_response}' with exception '{str(e)}'",
                    }
                )
            else:
                return response

        logger.debug(f"<-- {json_response}")

        return json_response


class CreateOrder:
    V1Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    V2Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    V3Order = Order(uuid="uuid", state="state", out_amount="btc_amount")
    apis = {"v1": V1Order, "v2": V2Order, "v3": V3Order}

    @classmethod
    def get(cls, data, api):
        order = cls.apis[api]
        if not order:
            return None
        uuid = data.get(order.uuid, None)
        state = data.get(order.state, None)
        out_amount = data.get(order.out_amount, None)

        return Order(uuid=uuid, state=state, out_amount=out_amount)


class OrderStatus:
    V1Status = StatusClass(
        state="state",
        in_out_rate="xmr_price_btc",
        payment_subaddress="xmr_receiving_subaddress",
        payment_address="xmr_receiving_address",
        payment_integrated_address="",
        payment_id_long="xmr_required_payment_id",
        payment_id_short="",
        in_amount="xmr_amount_total",
        in_amount_remaining="xmr_amount_remaining",
        in_confirmations_remaining="xmr_num_confirmations_remaining",
    )
    V2Status = StatusClass(
        state="state",
        in_out_rate="xmr_price_btc",
        payment_subaddress="xmr_receiving_subaddress",
        payment_address="xmr_receiving_address",
        payment_integrated_address="xmr_receiving_integrated_address",
        payment_id_long="xmr_required_payment_id_long",
        payment_id_short="xmr_required_payment_id_short",
        in_amount="xmr_amount_total",
        in_amount_remaining="xmr_amount_remaining",
        in_confirmations_remaining="xmr_num_confirmations_remaining",
    )
    V3Status = StatusClass(
        state="state",
        in_out_rate="incoming_price_btc",
        payment_subaddress="receiving_subaddress",
        payment_address="receiving_address",
        payment_integrated_address="receiving_integrated_address",
        payment_id_long="required_payment_id_long",
        payment_id_short="required_payment_id_short",
        in_amount="incoming_amount_total",
        in_amount_remaining="remaining_amount_incoming",
        in_confirmations_remaining="incoming_num_confirmations_remaining",
    )


    apis = {"v1": V1Status, "v2": V2Status, "v3": V3Status}
    api_classes = {"v1": StatusClass, "v2": StatusClass, "v3": StatusClass}

    @classmethod
    def get(cls, data, api):
        status = cls.apis[api]
        StatusClass_ = cls.api_classes[api]
        if not status:
            return None
        state = data.get(status.state, None)
        in_out_rate = data.get(status.in_out_rate, None)
        in_confirmations_remaining = data.get(
            status.in_confirmations_remaining, None
        )
        in_amount_remaining = data.get(status.in_amount_remaining, None)
        in_amount = data.get(status.in_amount, None)
        payment_id_short = data.get(status.payment_id_short, None)
        payment_id_long = data.get(status.payment_id_long, None)
        payment_integrated_address = data.get(
            status.payment_integrated_address, None
        )
        payment_address = data.get(status.payment_address, None)
        payment_subaddress = data.get(status.payment_subaddress, None)

        return StatusClass_(
            state=state,
            in_out_rate=in_out_rate,
            in_confirmations_remaining=in_confirmations_remaining,
            in_amount_remaining=in_amount_remaining,
            in_amount=in_amount,
            payment_id_short=payment_id_short,
            payment_id_long=payment_id_long,
            payment_integrated_address=payment_integrated_address,
            payment_address=payment_address,
            payment_subaddress=payment_subaddress,
        )


class CheckPrice:
    V1Price = None
    V2Price = Price(
        out_amount="btc_amount",
        in_amount="xmr_amount_total",
        in_out_rate="xmr_price_btc",
    )
    V3Price = Price(
        out_amount="btc_amount",
        in_amount="incoming_amount_total",
        in_out_rate="incoming_price_btc",
    )
    apis = {"v1": V1Price, "v2": V2Price, "v3": V3Price}

    @classmethod
    def get(cls, data, api):
        price = cls.apis[api]
        if not price:
            return None
        out_amount = data.get(price.out_amount, None)
        in_amount = data.get(price.in_amount, None)
        in_out_rate = data.get(price.in_out_rate, None)

        return Price(
            out_amount=out_amount, in_amount=in_amount, in_out_rate=in_out_rate
        )


class CheckQrCode:
    @classmethod
    def get(cls, data, api):
        return data


class XmrtoApi:
    CREATE_ORDER_ENDPOINT = "/api/{api_version}/xmr2btc/order_create/"
    ORDER_STATUS_ENDPOINT = "/api/{api_version}/xmr2btc/order_status_query/"
    ORDER_CHECK_PRICE_ENDPOINT = (
        "/api/{api_version}/xmr2btc/order_check_price/"
    )
    QRCODE_ENDPOINT = "/api/{api_version}/xmr2btc/gen_qrcode"

    def __init__(self, url="https://xmr.to", api="v2"):
        self.url = url
        self.api = api
        self.__xmr_conn = XmrtoConnection()

    def create_order(self, out_address=None, out_amount=None):
        if out_address is None:
            return None
        if out_amount is None:
            return None
        create_order_url = self.url + self.CREATE_ORDER_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"btc_dest_address": out_address, "btc_amount": str(out_amount)}

        response = self.__xmr_conn.post(
            url=create_order_url, postdata=postdata,
        )

        return CreateOrder.get(data=response, api=self.api)

    def order_status(self, uuid=None):
        if uuid is None:
            return None
        order_status_url = self.url + self.ORDER_STATUS_ENDPOINT.format(
            api_version=self.api
        )
        postdata = {"uuid": uuid}

        response = self.__xmr_conn.post(
            url=order_status_url, postdata=postdata,
        )

        return OrderStatus.get(data=response, api=self.api)

    def order_check_price(self, pay_amount=None):
        if pay_amount is None:
            print("asdfsfafsf")
            return None
        order_check_price_url = (
            self.url
            + self.ORDER_CHECK_PRICE_ENDPOINT.format(api_version=self.api)
        )
        postdata = {"btc_amount": str(pay_amount)}
        response = self.__xmr_conn.post(
            url=order_check_price_url, postdata=postdata,
        )

        return CheckPrice.get(data=response, api=self.api)

    def generate_qrcode(self, data=None):
        if data is None:
            return None
        generate_qrcode_url = (
            self.url
            + self.QRCODE_ENDPOINT.format(api_version=self.api)
            + f"?data={data}"
        )
        response = self.__xmr_conn.get(
            url=generate_qrcode_url,
            expect_json=False
        )

        return CheckQrCode.get(data=response, api=self.api)

class OrderStateType(type):

    @property
    def TO_BE_CREATED(cls):
        return "TO_BE_CREATED"

    @property
    def UNPAID(cls):
        return "UNPAID"

    @property
    def UNDERPAID(cls):
        return "UNDERPAID"

    @property
    def PAID_UNCONFIRMED(cls):
        return "PAID_UNCONFIRMED"

    @property
    def BTC_SENT(cls):
        return "BTC_SENT"

    @property
    def TIMED_OUT(cls):
        return "TIMED_OUT"

    @property
    def PURGED(cls):
        return "PURGED"


class XmrtoOrderStatus():
    def __init__(self, url="https://xmr.to", api="v2", uuid=None):
        self.api = XmrtoApi(url=url, api=api)
        self.uuid = uuid
        self.order_status = None

        self.in_amount = None
        self.in_amount_remaining = None
        self.payment_subaddress = None
        self.payment_address = None
        self.payment_integrated_address = None
        self.state = XmrtoOrder.TO_BE_CREATED
        
    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid
        self.order_status = self.api.order_status(
            uuid=uuid
        )

        if self.order_status:
            self.in_amount = self.order_status.in_amount
            self.in_amount_remaining = self.order_status.in_amount_remaining
            self.in_out_rate = self.order_status.in_out_rate
            self.payment_address = self.order_status.payment_address
            self.payment_subaddress = self.order_status.payment_subaddress
            self.payment_integrated_address = self.order_status.payment_integrated_address
            self.state = self.order_status.state

    def __str__(self):
        data = {"uuid": self.uuid, "state": self.state}
        if self.order_status:
            if self.order_status.payment_subaddress:
                data["payment_subaddress"] = self.order_status.payment_subaddress
            if self.order_status.payment_address:
                data["payment_address"] = self.order_status.payment_address
            if self.order_status.payment_integrated_address:
                data["payment_integrated_address"] = self.order_status.payment_integrated_address
            if self.order_status.in_amount:
                data["in_amount"] = self.order_status.in_amount
            if self.order_status.in_amount_remaining:
                data["in_amount_remaining"] = self.order_status.in_amount_remaining

        return json.dumps(data)


class XmrtoOrder(metaclass=OrderStateType):
    def __init__(
        self, url="https://xmr.to", api="v2", out_address=None, out_amount=None
    ):
        self.url = url
        self.api = api
        self.xmrto_api = XmrtoApi(url=self.url, api=self.api)
        self.order = None
        self.order_status = None

        self.out_address = out_address
        self.out_amount = out_amount
        self.uuid = None
        self.in_amount = None
        self.in_amount_remaining = None
        self.payment_subaddress = None
        self.payment_address = None
        self.payment_integrated_address = None
        self.state = XmrtoOrder.TO_BE_CREATED
        self.all = None

    def create_order(self, out_address=None, out_amount=None):
        if out_address is None:
            out_address = self.out_address
        if out_amount is None:
            out_amount = self.out_amount

        self.order = self.xmrto_api.create_order(
            out_address=out_address, out_amount=out_amount
        )
        if self.order:
            self.uuid = self.order.uuid
            self.state = self.order.state


    def get_order_status(self, uuid=None):
        if uuid is None:
            uuid = self.uuid
        self.order_status = XmrtoOrderStatus(url=self.url, api=self.api)
        self.order_status.get_order_status(uuid=uuid)
        if self.order_status:
            self.state = self.order_status.state

    def __str__(self):
        data = {"uuid": self.uuid, "state": self.state, "btc_address": self.out_address, "btc_amount": self.out_amount}
        if self.order_status:
            if self.order_status.payment_subaddress:
                data["payment_subaddress"] = self.order_status.payment_subaddress
            if self.order_status.payment_address:
                data["payment_address"] = self.order_status.payment_address
            if self.order_status.payment_integrated_address:
                data["payment_integrated_address"] = self.order_status.payment_integrated_address
            if self.order_status.in_amount:
                data["in_amount"] = self.order_status.in_amount
            if self.order_status.in_amount_remaining:
                data["in_amount_remaining"] = self.order_status.in_amount_remaining

        return json.dumps(data)


def create_order(
    xmrto_url=XMRTO_URL,
    api_version=API_VERSION,
    out_address=DESTINATION_ADDRESS,
    out_amount=PAY_AMOUNT,
    xmr_amount=XMR_AMOUNT,
):
    order = XmrtoOrder(
        url=xmrto_url, api=api_version,
        out_address=out_address, out_amount=out_amount
    )
    order.create_order()
    logger.debug(f"XMR.to order: {order}")

    order.get_order_status()
    logger.debug(f"Order created: {order.uuid}")

    return order


def track_order(
    xmrto_url=XMRTO_URL,
    api_version=API_VERSION,
    uuid=None,
):
    order_status = XmrtoOrderStatus(
        url=xmrto_url, api=api_version,
        uuid=uuid
    )
    order_status.get_order_status()
    return order_status


def order_check_price(
    xmrto_url=XMRTO_URL, api_version=API_VERSION, out_amount=PAY_AMOUNT
):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    return xmrto_api.order_check_price(pay_amount=out_amount)


def generate_qrcode(xmrto_url=XMRTO_URL, api_version=API_VERSION, data=None):
    xmrto_api = XmrtoApi(url=xmrto_url, api=api_version)

    qrcode = xmrto_api.generate_qrcode(data=data)
    if not qrcode:
        print("No data provided to convert to qrcode.")
    with open("qrcode.png", "wb") as qrcode_file:
        for chunk in qrcode:
            qrcode_file.write(chunk)
    print("Stored qrcode in qrcode.png.")

if __name__ == "__main__":
    if CREATE_AND_TRACK_ORDER:
        try:
            order = create_order()
            order.get_order_status()
            if order:
                while not order.state == XmrtoOrder.BTC_SENT:
                    print(order)
                    time.sleep(3)
                    order.get_order_status()
        except (KeyboardInterrupt) as e:
            print(f"\nUser interrupted\n{order}")
    if CREATE_ORDER:
        order = create_order()
        print(order)
    elif TRACK_ORDER:
        print(track_order(uuid=SECRET_KEY))
    elif GET_PRICE:
        print(order_check_price())
    elif CREATE_QRCODE:
        generate_qrcode(xmrto_url=XMRTO_URL, api_version=API_VERSION, data=QR_DATA)

