from xml.etree import ElementTree

from scripts.ci.emit_pytest_annotations import _message


def test_failure_message_is_read_from_junit_element() -> None:
    testcase = ElementTree.fromstring(
        '<testcase classname="integration-tests.test_example" name="test_case">'
        '<failure message="assert 1 == 2" />'
        "</testcase>"
    )

    assert _message(testcase) == "assert 1 == 2"
