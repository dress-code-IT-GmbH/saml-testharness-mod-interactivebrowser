"""
Demo driver for the interactive browser test module.

test_target: The URL that will be queried. The response will then be given
to the interactive browser to proceed.

"""
from future.standard_library import install_aliases

from testharness_mod_interactivebrowser.module import ContentHandler, AutoCloseUrls
import mechanize

install_aliases()
from urllib.request import urlopen
from http.cookiejar import CookieJar


from fwclasses import MyHandlerResponse, ConvLog, MyCookieJar

target_path =  "http://www.warwaris.at/brtest/"

if __name__ == "__main__":


	conv_log = ConvLog()

	request_url = target_path + "brtest.php"
	request_url = "https://www.cacert.org/"

	urllib_request = mechanize.Request(request_url)
	urllib_response = mechanize.urlopen(urllib_request)

	cookie_jar = MyCookieJar()
	handler_response = MyHandlerResponse('driver', MyHandlerResponse.FAILED_NEXT,
							cookie_jar = cookie_jar,
							urllib_request = urllib_request,
							urllib_response = urllib_response )
	
	print handler_response.response_content_type()

	conv_log.log_response(handler_response)

	# retrieving ./ack.txt from the server will end the test too
	auto_close_urls = AutoCloseUrls()
	auto_close_urls.add(target_path + 'ack', 200, True)

	# init and run the test
	test = ContentHandler(None, conv_log)
	result = test.handle_response(conv_log, auto_close_urls, verify_ssl=True, cookie_jar=cookie_jar)

	print ( "Test result user action: " + result.user_action )
	