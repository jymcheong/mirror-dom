"""
Testing the javascript functionality of the mirrordom library
"""

import json
import os
import time

from selenium.common.exceptions import NoSuchElementException

import util

def setupModule():
    util.start_webserver()

def teardownModule():
    util.stop_webserver()

class TestJavascriptFF(util.TestBrowserBase):

    HTML_FILE = "test_javascript.html"

    # The file INSIDE the broadcaster iframe
    HTML_CONTENT_FILE = "test_javascript_content.html"

    @classmethod
    def _create_webdriver(cls):
        return util.get_debug_firefox_webdriver()

    def test_webdriver_works(self):
        """ Test 0: Sometimes this is the real problem """
        self.init_webdriver()
        value = self.webdriver.execute_script("return 1")

    def test_fetch_document(self):
        """ Test 1: Just make sure fetching works """
        self.init_webdriver()

        # Right now, browser_html should be the raw inner html
        browser_html = self.webdriver.execute_script("return test_1_get_broadcaster_document()")

        # Compare it to the actual HTML file
        html_path = util.get_html_path(self.HTML_CONTENT_FILE)
        actual_html = open(html_path, 'r').read()

        assert self.compare_html(actual_html, browser_html)


    # Note that I've deliberately omitted <tbody> from the table element, as I
    # want to see what sort of complications ensue
    TEST_APPLY_DOCUMENT = """\
    <html>
      <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type"></meta>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.7.2/jquery.min.js" type="text/javascript"></script>
        <script type="text/javascript"></script>
        <style type="text/css">table { border-collapse: collapse; }
        table,th,td { border: 1px solid black; }</style>
      </head>
      <body>
        <h3>Hallow world!</h3>
        <div>
        ohay
          <table id="thetable" style="border: 1px solid pink;">
          <tr>
            <th>1</th>
            <th>2</th>
          </tr>
          <tr>
            <td>a</td>
            <td>b</td>
          </tr>
          <tr>
            <td>c</td>
            <td>d</td>
          </tr>
          </table>
        </div>
        <div>
          <input id="thetextinput" length="50" type="text" value="hello"></input>
        </div>
        <a href="test_dom_sync_content2.html">Page 2</a>
      </body>
    </html>"""

    def test_apply_document(self):
        """ Test 2: Apply document to viewer """
        self.init_webdriver()
        desired_html = self.TEST_APPLY_DOCUMENT
        self.webdriver.execute_script("test_2_apply_document(arguments[0])", desired_html)
        viewer_html = self.webdriver.execute_script("return get_viewer_html()")
        assert self.compare_html(desired_html, viewer_html, clean=True)

    def test_get_diff_add_node(self):
        """ Test 3: Diff of adding a node """
        self.init_webdriver()
        # This triggers clone_dom() in the broadcaster js object, so that diffing works
        self.webdriver.execute_script("test_1_get_broadcaster_document()")
        self.webdriver.execute_script("test_3_modify_broadcaster_document_with_add_node()")
        result = self.webdriver.execute_script("return test_3_get_broadcaster_diff()")
        result = json.loads(result)
        print result

        # Expected result should be similar to:
        # [[u'node', [1, 5], u'Hello Dog', {u'attributes': {}, u'nodeType': 1,
        #   u'nodeName': u'DIV', u'nodeValue': None}, [[u'props', [],
        #   {u'style.cssText': u'background-color: blue;'}, None]]]]
        #
        # I don't really want to hardcode an exact result comparison at this
        # point in time
        assert len(result) == 1
        props = result[0][4]

        # test_3_modify_broadcaster_document_with_add_node adds background-color style
        # which should reflect in props
        assert len(props) == 1
        prop, prop_path, changed_props, removed_props = props[0]
        assert "style.cssText" in changed_props
        # The path should be empty as the style applies directly to the node
        assert prop_path == []

    def test_apply_add_node_diff(self):
        """ Test 4: Apply a simple add node diff """
        self.init_webdriver()
        diff = [[u'node', [1, 4], u'Hello There', {u'attributes': {u'style':
            u'background-color: red;'}, u'nodeType': 1, u'nodeName': u'DIV',
            u'nodeValue': None}, []]]
        self.webdriver.execute_script("test_4_setup_viewer_document()")
        self.webdriver.execute_script("test_4_apply_viewer_diff(arguments[0])",
                json.dumps(diff))

    def test_get_initial_property_diff(self):
        """ Test 5: Retrieve initial property diff """
        self.init_webdriver()
        result = self.webdriver.execute_script("return test_5_get_broadcaster_all_property_diff()")
        result = json.loads(result)
        print result

        # CSS rules only
        assert all(d[0] == "props" for d in result)

        # Should be a border in there somewhere (note: IE returns individual
        # border rules for each side, FF retains the single border rule)
        assert util.diff_contains_changed_property_value(result, "border")

        # Make sure there's no crud making it through
        assert not util.diff_contains_empty_attr_prop_values(result)

        # One inline style has been defined against the table, there should be
        # a "value" property against the input element as well
        assert len(result) >= 1

    def test_get_diff_styles(self):
        """ Test 6: Retrieve document with dynamically modified styles """
        self.init_webdriver()
        # This triggers clone_dom() in the broadcaster js object, so that diffing works
        self.webdriver.execute_script("test_1_get_broadcaster_document()")
        self.webdriver.execute_script("test_6_modify_broadcaster_document_with_css()")
        result = self.webdriver.execute_script("return test_3_get_broadcaster_diff()")
        result = json.loads(result)
        print result
        assert len(result) == 2

    def test_get_diff_attributes(self):
        """ Test 7: Diff of attributes """
        self.init_webdriver()
        # This triggers clone_dom() in the broadcaster js object, so that diffing works
        self.webdriver.execute_script("test_1_get_broadcaster_document()")
        self.webdriver.execute_script("test_7_modify_broadcaster_document_with_attribute()")
        result = self.webdriver.execute_script("return test_3_get_broadcaster_diff()")
        result = json.loads(result)
        print result
        assert len(result) > 0

    def test_get_diff_properties(self):
        """ Test 8: Diff of properties """
        self.init_webdriver()
        # This triggers clone_dom() in the broadcaster js object, so that diffing works
        self.webdriver.execute_script("test_1_get_broadcaster_document()")

        new_value = "-ae9ij"

        # Change text input value
        self.webdriver.switch_to_frame('broadcaster_iframe')
        input = self.webdriver.find_element_by_id('thetextinput')
        input.send_keys(new_value)
        #self.webdriver.execute_script("test_8_modify_broadcaster_document_with_property()")

        # Get the diff
        self.webdriver.switch_to_default_content()
        result = self.webdriver.execute_script("return test_3_get_broadcaster_diff()")
        result = json.loads(result)
        print result

        # Should be there
        assert util.diff_contains_changed_property_value(result, new_value)

    def test_get_diff_delete_node(self):
        """ Test 9: Diff of deleting nodes """
        self.init_webdriver()
        # This triggers clone_dom() in the broadcaster js object, so that diffing works
        self.webdriver.execute_script("test_1_get_broadcaster_document()")
        self.webdriver.execute_script("test_9_modify_broadcaster_document_with_delete_node()")
        result = self.webdriver.execute_script("return test_3_get_broadcaster_diff()")
        result = json.loads(result)
        print result
        assert len(result) > 0

    def test_apply_property_diff(self):
        """ Test 10: Apply a property diff """
        self.init_webdriver()
        new_value = "gSE_AU*)EHGSIODNGO"
        # Assuming that the <input id="thetextinput">  element is at position
        # [1,2,0] in test_javascript_content_sanitised.html
        diff = [[u'props', [1, 2, 0], {u'value': new_value}, None]]
        self.webdriver.execute_script("test_4_setup_viewer_document()")

        # Value should be default to "hello"
        self.webdriver.switch_to_frame('viewer_iframe')
        input = self.webdriver.find_element_by_id('thetextinput')
        input_value = input.get_attribute("value")
        assert input_value == "hello"
        print "Initial value: %s" % (input_value)

        # Ok, change the property
        self.webdriver.switch_to_default_content()
        self.webdriver.execute_script("test_4_apply_viewer_diff(arguments[0])",
                json.dumps(diff))

        # Now let's check it out
        self.webdriver.switch_to_frame('viewer_iframe')
        input = self.webdriver.find_element_by_id('thetextinput')
        input_value = input.get_attribute("value")
        print "Got: %s" % (input_value)
        assert input_value == new_value

    def test_apply_attribute_diff(self):
        """ Test 11: Apply a property diff """
        self.init_webdriver()
        new_value = "4"
        # Assuming that the <table id="thetable">  element is at position
        # [1,1,1] in test_javascript_content_sanitised.html. This should
        # change cellSpacing to 4
        diff = [[u'attribs', [1, 1, 1], {u'cellSpacing': new_value}, []]]
        self.webdriver.execute_script("test_4_setup_viewer_document()")

        # Cellspacing shouldn't be set yet
        self.webdriver.switch_to_frame('viewer_iframe')
        table = self.webdriver.find_element_by_id('thetable')
        table_cellspacing = table.get_attribute("cellspacing")
        print "Cellspacing before: %s" % (table_cellspacing)
        assert table_cellspacing == None

        # Ok, change the attrib
        self.webdriver.switch_to_default_content()
        self.webdriver.execute_script("test_4_apply_viewer_diff(arguments[0])",
                json.dumps(diff))

        # Now let's check it out
        self.webdriver.switch_to_frame('viewer_iframe')
        table = self.webdriver.find_element_by_id('thetable')
        table_cellspacing = table.get_attribute("cellspacing")
        print "Cellspacing after: %s" % (table_cellspacing)
        assert table_cellspacing == new_value
        
    def test_apply_delete_node_diff(self):
        """ Test 12: Apply a delete diff
        
        WARNING: This test is brittle if you're modifying the test HTML
        Try to make sure <div id="thelastelement"> is always the last element
        in the <body>.
        """
        self.init_webdriver()
        
        # This should delete the <a id="textinput"> at the end of the page
        diff = [[u'deleted', [1, 4]]]
        self.webdriver.execute_script("test_4_setup_viewer_document()")

        # Just make sure it's there first
        self.webdriver.switch_to_frame('viewer_iframe')
        div = self.webdriver.find_element_by_id('thelastelement')
        assert div != None

        self.webdriver.switch_to_default_content()
        self.webdriver.execute_script("test_4_apply_viewer_diff(arguments[0])",
                json.dumps(diff))

        # Shouldn't be there now
        self.webdriver.switch_to_frame('viewer_iframe')
        try:
            div = self.webdriver.find_element_by_id('thelastelement')
        except NoSuchElementException:
            div_exists = False
        else:
            div_exists = True

        assert not div_exists

    def test_get_and_apply_initial_property_diff(self):
        """
        Test 13: Get and set initial property diff

        This is mainly testing that the ipaths in the get_property_diffs value
        are correct.
        """
        new_value = "sdfgsdfogj"

        self.init_webdriver()
        self.webdriver.execute_script("test_4_setup_viewer_document()")

        # Value should be default to "hello"
        self.webdriver.switch_to_frame('broadcaster_iframe')
        input = self.webdriver.find_element_by_id('thetextinput')
        initial_value = input.get_attribute("value")
        input.send_keys(new_value)
        test_value = input.get_attribute("value")
        assert test_value == initial_value + new_value
        print "Test value: %s" % (test_value)

        # Ok, change the property
        self.webdriver.switch_to_default_content()
        diff = self.webdriver.execute_script("return test_5_get_broadcaster_all_property_diff()")
        diff = json.loads(diff)
        print "Diff: %s"
        self.webdriver.execute_script("test_4_apply_viewer_diff(arguments[0])", json.dumps(diff))

        # Now let's check it out
        self.webdriver.switch_to_frame('viewer_iframe')
        input = self.webdriver.find_element_by_id('thetextinput')
        input_value = input.get_attribute("value")
        print "Got: %s" % (input_value)
        assert input_value == test_value

class TestJavascriptIE(TestJavascriptFF):

    @classmethod
    def _create_webdriver(cls):
        return util.get_debug_ie_webdriver()