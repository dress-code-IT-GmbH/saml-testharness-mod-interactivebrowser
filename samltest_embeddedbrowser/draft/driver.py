"""
Demo driver for the interactive browser test module.

test_target: The URL that will be queried. The response will then be given
to the interactive browser to proceed.

Limitations:
Handling http post is on the todo list

"""
from future.standard_library import install_aliases

from testharness_mod_interactivebrowser.module import ContentHandler, AutoCloseUrls

install_aliases()
<<<<<<< HEAD
from urllib.request import urlopen
from http.cookiejar import CookieJar


from fwclasses import MyHandlerResponse, ConvLog, MyCookieJar
=======
from urllib.request import Request, urlopen
>>>>>>> c067f38c411a881905999d5677e89277bd689561

target_path =  "http://www.warwaris.at/brtest/"


if __name__ == "__main__":

<<<<<<< HEAD

	conv_log = ConvLog()
	cookie_jar = MyCookieJar()
=======
	request_url = target_path + "brtest.php"
	#request_url = "https://www.cacert.org/"

	http_request = Request(request_url)
	http_response = urlopen(http_request)
>>>>>>> c067f38c411a881905999d5677e89277bd689561

	request_url = target_path + "brtest.php"
	#request_url = "https://www.cacert.org/"

	"""
	Simulating some other content handler, which fails on a given request url
	"""
	
	urllib_request = mechanize.Request(request_url)
	urllib_response = mechanize.urlopen(urllib_request)
	cookie_jar.extract_cookies(urllib_response,urllib_request)
	
	handler_response = MyHandlerResponse('test-driver', MyHandlerResponse.FAILED_NEXT,
							cookie_jar = cookie_jar,
							urllib_request = urllib_request,
							urllib_response = urllib_response )
	
	conv_log.log_response(handler_response)

	"""
	Preparing and calling the EB module
	"""

	auto_close_urls = AutoCloseUrls()
	auto_close_urls.add(target_path + 'ack', 200, True)

	test = ContentHandler(None, conv_log)
	result = test.handle_response(conv_log, auto_close_urls, verify_ssl=True, cookie_jar=cookie_jar)

	print ( "Test result user action: " + result.user_action )
