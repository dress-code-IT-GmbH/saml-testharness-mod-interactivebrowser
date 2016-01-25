"""
Demo driver for the interactive browser test module.

test_target: The URL that will be queried. The response will then be given
to the interactive browser to proceed.

"""
from future.standard_library import install_aliases

from testharness_mod_interactivebrowser.module import TestAction, AutoCloseUrls

install_aliases()
from urllib.request import urlopen

target_path =  "http://www.warwaris.at/brtest/"

if __name__ == "__main__":

	test_target = target_path + "brtest.php"

	response = urlopen(test_target)


	# retrieving ./ack.txt from the server will end the test too
	autocloseurls = AutoCloseUrls()
	autocloseurls.add(target_path + 'ack', 200, True)

	# init and run the test
	test = TestAction(autocloseurls)
	result = test.run(response,test_target)

	if result:
		print ("Test: OK")
	else:
		print ("Test: Failed")