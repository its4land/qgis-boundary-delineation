# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Its4landAPI
 Query its4land Land Administration Data
                              -------------------
        begin                : 2019-04-14
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Ivan Ivanov suricactus
        email                : ivan.ivanov@suricactus.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from typing import Any, Optional, Dict
from enum import Enum
from urllib.parse import urljoin

import requests

class ResponseType(Enum):
    json = 1
    text = 2
    html = 3
    stream = 4


Payload = Dict[str, Any]


class Its4landAPI:
    def __init__(self, url: str, api_key: str, response_type: ResponseType = ResponseType.json):
        self.url = url + '/'
        self.api_key = api_key
        self.response_type = response_type

    def get(self,
            data: Optional[Payload],
            encode_as: str = 'form',
            response_type: ResponseType = None,
            files: dict = None,
            url: str = None):
        url = url or self.url
        response_type = response_type or self.response_type

        try:
            send_data: Dict[str, Any] = {
                'stream': (response_type == ResponseType.stream),
            }

            if encode_as == 'json':
                send_data['json'] = data
            elif encode_as == 'form':
                send_data['data'] = data
            else:
                raise Exception(url, 998, 'Unknown encode type: %s' % encode_as)

            if files is not None and len(files):
                send_data['files'] = {}

                for k, v in files.items():
                    try:
                        send_data['files'][k] = open(v, 'rb')
                    except Exception as e:
                        raise Exception(url, 998, 'Unable to open file: %s' % v, e)

            resp = requests.get(url, **send_data)

            if resp is not None:
                if resp.ok and resp.content is not None:
                    print(url)
                    print('__________')
                    if response_type == ResponseType.stream:
                        return resp
                    elif response_type == ResponseType.json:
                        return resp.json()
                    elif response_type == ResponseType.html:
                        return resp.content
                    else:
                        raise Exception(resp.url, resp.status_code, resp.reason)
                raise Exception(resp.url, resp.status_code, resp.reason)

            else:
                raise Exception(resp.url, 999, 'Unknown exception')
        except Exception as e:
            raise Exception(url, 999, 'Unknown exception', e)

    def get_projects(self):
        return self.get(None, url=urljoin(self.url, 'projects'))

    def get_validaiton_sets(self):
        return self.get(None, url=urljoin(self.url, 'WP5ValidationSets'))

    def download_file(self, data: Optional[Payload], filename: str, **rest) -> str:
        resp = self.get(data, response_type=ResponseType.stream, **rest)

        with open(filename, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=4096):
                if not chunk:  # filter out keep-alive new chunks
                    pass

                f.write(chunk)

        return filename