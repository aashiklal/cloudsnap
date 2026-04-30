import pytest

from backend.tag_commands import (
    TagCommandError,
    apply_tag_mutation,
    has_any_tag,
    parse_modify_tag_command,
    parse_search_tag_command,
    tags_satisfy_query,
)


def test_parse_search_tag_command_orders_and_normalizes_tags():
    command = parse_search_tag_command({
        'tag2': 'Cat',
        'tag2count': '3',
        'tag1': 'Dog',
        'tag1count': '1',
    })

    assert command == [
        {'tag': 'dog', 'count': 1},
        {'tag': 'cat', 'count': 3},
    ]


def test_parse_search_tag_command_rejects_missing_count():
    with pytest.raises(TagCommandError) as exc:
        parse_search_tag_command({'tag1': 'cat'})

    assert exc.value.message == 'Missing tag1count for tag1'
    assert exc.value.status_code == 400


def test_parse_modify_tag_command_validates_and_normalizes_counts():
    action_type, commands = parse_modify_tag_command({
        'type': '1',
        'tag1': 'new tag',
        'tag1count': '2',
    })

    assert action_type == 1
    assert commands == [{'tag': 'new tag', 'count': 2}]


def test_parse_modify_tag_command_rejects_invalid_type():
    with pytest.raises(TagCommandError) as exc:
        parse_modify_tag_command({'type': '2', 'tag1': 'cat', 'tag1count': 1})

    assert exc.value.message == 'Invalid type: must be 0 (remove) or 1 (add)'


def test_apply_tag_mutation_adds_and_removes_by_case_insensitive_name():
    tags = apply_tag_mutation(
        [{'tag': 'Dog', 'count': 2}, {'tag': 'cat', 'count': 1}],
        1,
        [{'tag': 'dog', 'count': 3}],
    )
    tags = apply_tag_mutation(tags, 0, [{'tag': 'CAT', 'count': 1}])

    assert tags == [{'tag': 'Dog', 'count': 5}]


def test_tags_satisfy_query_requires_all_requested_counts():
    assert tags_satisfy_query(
        [{'tag': 'dog', 'count': 2}, {'tag': 'cat', 'count': 1}],
        [{'tag': 'dog', 'count': 2}, {'tag': 'cat', 'count': 1}],
    )
    assert not tags_satisfy_query(
        [{'tag': 'dog', 'count': 1}, {'tag': 'cat', 'count': 1}],
        [{'tag': 'dog', 'count': 2}],
    )


def test_has_any_tag_matches_case_insensitively():
    assert has_any_tag([{'tag': 'Dog', 'count': 1}], {'dog', 'cat'})
    assert not has_any_tag([{'tag': 'bird', 'count': 1}], {'dog', 'cat'})
