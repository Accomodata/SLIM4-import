import base64
import json
import datetime


def encode_skiptoken(write_date, record_id):
    """Encode keyset pagination values as a Base64 JSON token."""
    payload = {
        'write_date': write_date.isoformat(),
        'id': record_id,
    }
    token_json = json.dumps(payload, separators=(',', ':'))
    return base64.b64encode(token_json.encode('utf-8')).decode('ascii')


def decode_skiptoken(skiptoken):
    """Decode and validate a Base64 JSON keyset pagination token."""
    try:
        payload = json.loads(
            base64.b64decode(skiptoken, validate=True).decode('utf-8'),
        )
        last_write_date = datetime.fromisoformat(payload['write_date'])
        last_id = payload['id']

        if isinstance(last_id, bool) or not isinstance(last_id, int):
            raise ValueError('id must be an integer')

    except Exception as error:
        raise ValueError(
            'Invalid $skiptoken: expected Base64 JSON with an ISO write_date '
            'and an integer id.',
        ) from error

    return last_write_date, last_id
