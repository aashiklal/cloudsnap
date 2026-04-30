from __future__ import annotations

import re
from typing import Iterable

TAG_PATTERN = re.compile(r'^tag[1-9][0-9]*$')
COUNT_PATTERN = re.compile(r'^tag[1-9][0-9]*count$')
MODIFY_TAG_PATTERN = re.compile(r'^tag\d+$')
TAG_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 _-]{1,64}$')
NUMERIC_PATTERN = re.compile(r'^[0-9]+$')


class TagCommandError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def parse_search_tag_command(parameters: dict) -> list[dict]:
    tags = {k: v for k, v in parameters.items() if TAG_PATTERN.match(k)}
    tagcounts = {k: v for k, v in parameters.items() if COUNT_PATTERN.match(k)}

    if not tags:
        raise TagCommandError('At least one tag is required')

    indices = sorted(int(k[3:]) for k in tags)
    for i in indices:
        if f'tag{i}count' not in tagcounts:
            raise TagCommandError(f'Missing tag{i}count for tag{i}')
        if f'tag{i}' not in tags:
            raise TagCommandError(f'Missing tag{i} for tag{i}count')

    if len(tags) != len(tagcounts):
        raise TagCommandError('Mismatched number of tags and counts')

    for tag, value in tags.items():
        if not TAG_NAME_PATTERN.match(str(value)):
            raise TagCommandError(
                f'Invalid tag value for {tag}: must be alphanumeric '
                '(letters, numbers, spaces, hyphens, underscores, max 64 chars)'
            )

    for tagcount, value in tagcounts.items():
        if not NUMERIC_PATTERN.match(str(value)):
            raise TagCommandError(f'Invalid count value for {tagcount}: must be numeric')

    return [
        {'tag': str(tags[f'tag{i}']).lower(), 'count': int(tagcounts[f'tag{i}count'])}
        for i in indices
    ]


def parse_modify_tag_command(body: dict) -> tuple[int, list[dict]]:
    action_type_raw = body.get('type')

    if action_type_raw is None:
        raise TagCommandError('Missing required field: type')

    if str(action_type_raw) not in ('0', '1'):
        raise TagCommandError('Invalid type: must be 0 (remove) or 1 (add)')

    action_type = int(action_type_raw)
    indices = sorted({
        int(re.search(r'\d+', k).group())
        for k in body if MODIFY_TAG_PATTERN.match(k)
    })

    commands = []
    for i in indices:
        tag_key = f'tag{i}'
        count_key = f'tag{i}count'

        if count_key not in body:
            raise TagCommandError(f'Missing {count_key} for {tag_key}')

        tag_name = str(body[tag_key]).strip()
        if not TAG_NAME_PATTERN.match(tag_name):
            raise TagCommandError(
                f'Invalid tag name "{tag_name}": use letters, numbers, spaces, '
                'hyphens, underscores (max 64 chars)'
            )

        try:
            count = int(body[count_key])
        except (ValueError, TypeError):
            raise TagCommandError(f'{count_key} must be an integer')
        if count < 1:
            raise TagCommandError(f'{count_key} must be at least 1')

        commands.append({'tag': tag_name, 'count': count})

    return action_type, commands


def apply_tag_mutation(existing_tags: Iterable[dict], action_type: int, commands: Iterable[dict]) -> list[dict]:
    tags = [dict(tag) for tag in existing_tags]
    indices_to_remove = []

    for command in commands:
        tag_name = command['tag']
        count = command['count']

        for idx, tag in enumerate(tags):
            if str(tag.get('tag', '')).lower() == tag_name.lower():
                if action_type == 1:
                    tag['count'] += count
                else:
                    tag['count'] = max(0, tag['count'] - count)
                    if tag['count'] == 0:
                        indices_to_remove.append(idx)
                break
        else:
            if action_type == 1:
                tags.append({'tag': tag_name, 'count': count})

    for idx in sorted(set(indices_to_remove), reverse=True):
        tags.pop(idx)

    return tags


def tags_satisfy_query(record_tags: Iterable[dict], query_tags: Iterable[dict]) -> bool:
    normalized_tags = [
        {'tag': str(tag.get('tag', '')).lower(), 'count': int(tag.get('count', 0))}
        for tag in record_tags
    ]
    return all(
        any(tag['tag'] == query['tag'] and tag['count'] >= query['count'] for tag in normalized_tags)
        for query in query_tags
    )


def has_any_tag(record_tags: Iterable[dict], query_tag_names: set[str]) -> bool:
    record_tag_names = {str(tag.get('tag', '')).lower() for tag in record_tags}
    return bool(query_tag_names & record_tag_names)
