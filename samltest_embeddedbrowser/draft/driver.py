"""
Demo driver for the interactive browser test module.

test_target: The URL that will be queried. The response will then be given
to the interactive browser to proceed.

"""
from future.standard_library import install_aliases

from testharness_mod_interactivebrowser.module import ContentHandler, AutoCloseUrls

install_aliases()
from urllib.request import Request, urlopen

target_path =  "http://www.warwaris.at/brtest/"

if __name__ == "__main__":

	request_url = target_path + "brtest.php"
	#request_url = "https://www.cacert.org/"

	http_request = Request(request_url)
	http_response = urlopen(http_request)


	# retrieving ./ack.txt from the server will end the test too
	auto_close_urls = AutoCloseUrls()
	auto_close_urls.add(target_path + 'ack', 200, True)

	# init and run the test
	test = ContentHandler(None)
	result = test.handle_response(http_response, auto_close_urls, http_request,None,True)

	print ( "Test result user action: " + result.user_action )
