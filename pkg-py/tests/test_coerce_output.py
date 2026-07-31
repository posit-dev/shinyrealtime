from shinyrealtime._utils import _coerce_output


def test_string_passthrough():
    assert _coerce_output("hello") == "hello"


def test_dict_preserves_field_names():
    assert _coerce_output({"temp": 72, "cond": "sunny"}) == '{"temp": 72, "cond": "sunny"}'


def test_list_serialized_as_json_array():
    assert _coerce_output([1, 2, 3]) == "[1, 2, 3]"


def test_list_of_records():
    assert _coerce_output([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]) == \
        '[{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]'


def test_int_stringified():
    assert _coerce_output(42) == "42"


def test_float_stringified():
    assert _coerce_output(3.14) == "3.14"


def test_bool_stringified():
    # bool is stringified via str() rather than json.dumps to match R behavior
    assert _coerce_output(True) == "True"


def test_none_returns_fallback():
    assert _coerce_output(None) == "OK"


def test_empty_string_returns_fallback():
    assert _coerce_output("") == "OK"


def test_custom_fallback():
    assert _coerce_output(None, fallback="no-op") == "no-op"


def test_unserializable_returns_fallback():
    class NotJSONable:
        pass
    assert _coerce_output(NotJSONable()) == "OK"
