# encoding: utf-8
#
# Copyright (c) 2015 Safari Books Online. All rights reserved.
#
# This software may be modified and distributed under the terms
# of the 3-clause BSD license.  See the LICENSE file for details.

from __future__ import unicode_literals, with_statement

from contextlib import contextmanager
import os
import re
try:
    from unittest import mock
except ImportError:
    import mock

import pytest
import requests

import salesforce_bulk_api
from salesforce_bulk_api import (bulk_response_attribute,
                                 chunked,
                                 itercsv,
                                 SalesforceBulkJob)


@contextmanager
def override_environment(**kwargs):
    """Overrides the specified environment variables for the duration of the
    scope it's used in"""
    overridden = {}
    for key, value in kwargs.items():
        overridden[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    yield

    for key, value in overridden.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_salesforce_connection_sandbox_omitted():
    environment = {
        'SALESFORCE_USERNAME': 'testsalesforceuser',
        'SALESFORCE_PASSWORD': 'password123',
        'SALESFORCE_SECURITY_TOKEN': 'token123',
        'SALESFORCE_INSTANCE': 'foo.example.com'
    }
    with override_environment(**environment), \
         mock.patch('salesforce_bulk_api.Salesforce') as Salesforce:

        session = salesforce_bulk_api.salesforce_session()
        assert session == Salesforce.return_value
        Salesforce.assert_called_with(username='testsalesforceuser',
                                      password='password123',
                                      security_token='token123',
                                      instance='foo.example.com',
                                      sandbox=False,
                                      sf_version='34.0')

def test_salesforce_connection_sandbox():
    environment = {
        'SALESFORCE_USERNAME': 'testsalesforceuser',
        'SALESFORCE_PASSWORD': 'password123',
        'SALESFORCE_SECURITY_TOKEN': 'token123',
        'SALESFORCE_INSTANCE': 'foo.example.com',
        'SALESFORCE_SANDBOX': 'True'
    }
    with override_environment(**environment), \
         mock.patch('salesforce_bulk_api.Salesforce') as Salesforce:

        session = salesforce_bulk_api.salesforce_session()
        assert session == Salesforce.return_value
        Salesforce.assert_called_with(username='testsalesforceuser',
                                      password='password123',
                                      security_token='token123',
                                      instance='foo.example.com',
                                      sandbox=True,
                                      sf_version='34.0')

def test_salesforce_connection_not_sandbox():
    environment = {
        'SALESFORCE_USERNAME': 'testsalesforceuser',
        'SALESFORCE_PASSWORD': 'password123',
        'SALESFORCE_SECURITY_TOKEN': 'token123',
        'SALESFORCE_INSTANCE': 'foo.example.com',
        'SALESFORCE_SANDBOX': 'False'
    }
    with override_environment(**environment), \
         mock.patch('salesforce_bulk_api.Salesforce') as Salesforce:

        session = salesforce_bulk_api.salesforce_session()
        assert session == Salesforce.return_value
        Salesforce.assert_called_with(username='testsalesforceuser',
                                      password='password123',
                                      security_token='token123',
                                      instance='foo.example.com',
                                      sandbox=False,
                                      sf_version='34.0')


class XMLMatcher(object):
    """A matcher suitable for use with mock to assert that two XML documents
    as strings are effectively the same"""
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, other):
        clean = lambda xml: re.sub(r'>\s*\n+\s*<', '><', xml).strip()
        assert clean(other) == clean(self.expected)
        return True


def test_itercsv_always_emits_headers():
    """itercsv should always emit headers, even where there is no data"""
    assert list(itercsv(['Hello', 'World'], [])) == [b'Hello,World\r\n']

def test_itercsv_emits_data_lines():
    """itercsv should yield individual lines of CSV, with headers"""
    expected = [
        b'Hello,World\r\n',
        b'1,2\r\n',
        b'3,4\r\n'
    ]
    assert list(itercsv(['Hello', 'World'], [[1, 2], [3, 4]])) == expected


def test_chunked_empty():
    """chunked should handle empty iterables"""
    assert list(chunked(iter([]), 0)) == []
    assert list(chunked(iter([]), 1)) == []
    assert list(chunked(iter([]), 2)) == []

def test_chunked():
    """chunked should handle small chunk sizes"""
    examples = list(range(10))
    assert list(chunked(iter(examples), 0)) == examples
    assert list(chunked(iter(examples), 1)) == [[i] for i in examples]
    assert list(chunked(iter(examples), 2)) == [[0,1], [2,3], [4,5], [6,7], [8,9]]
    assert list(chunked(iter(examples), 3)) == [[0,1,2], [3,4,5], [6,7,8], [9]]
    assert list(chunked(iter(examples), 4)) == [[0,1,2,3], [4,5,6,7], [8,9]]
    assert list(chunked(iter(examples), 5)) == [[0,1,2,3,4], [5,6,7,8,9]]
    assert list(chunked(iter(examples), 6)) == [[0,1,2,3,4,5], [6,7,8,9]]
    assert list(chunked(iter(examples), 7)) == [[0,1,2,3,4,5,6], [7,8,9]]
    assert list(chunked(iter(examples), 8)) == [[0,1,2,3,4,5,6,7], [8,9]]
    assert list(chunked(iter(examples), 9)) == [[0,1,2,3,4,5,6,7,8], [9]]
    assert list(chunked(iter(examples), 10)) == [examples]
    assert list(chunked(iter(examples), 11)) == [examples]


def test_bulk_response_attributes():
    """The bulk_response_attribute utility should pluck out elements of a
    Salesforce Bulk API response, and raise if the element doesn't exist"""
    document = '''<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>THEJOBID</id>
            <operation>update</operation>
            <object>Lead</object>
        </jobInfo>
    '''
    assert bulk_response_attribute(document, 'id') == 'THEJOBID'
    assert bulk_response_attribute(document, 'object') == 'Lead'
    with pytest.raises(Exception):
        bulk_response_attribute(document, 'nothing')


@pytest.yield_fixture()
def salesforce_session():
    """Prepares a mock Salesforce session for the test suite"""
    with mock.patch('salesforce_bulk_api.salesforce_session') as salesforce_session:
        salesforce_session.return_value.session_id = 'the-session-id'
        salesforce_session.return_value.sf_version = '34.0'
        salesforce_session.return_value.base_url = 'https://salesforce/services/data/v34.0/'

        salesforce_session.return_value.describe.return_value = {
            'sobjects': [
                {'name': 'Lead'},
                {'name': 'Contact'}
            ]
        }

        yield salesforce_session

@pytest.yield_fixture()
def bulk_request():
    """Prepares a mock SalesforceBulkJob.request method for the test suite.
    Since all requests to Salesforce should go through this method, it should
    prevent the test suite from making any external HTTP calls."""
    with mock.patch('salesforce_bulk_api.SalesforceBulkJob.request') as request:
        yield request

@pytest.fixture()
def new_job(salesforce_session):
    """Prepares a new job in its default state"""
    return SalesforceBulkJob('update', 'Lead')

def test_instantiating_salesforce_bulk_job(new_job, salesforce_session, bulk_request):
    """Instantiating a SalesforceBulkJob should authenticate and prepare for creating jobs"""
    assert new_job.session_id == 'the-session-id'
    assert new_job.async_url == 'https://salesforce/services/async/34.0/'
    assert new_job.operation == 'update'
    assert new_job.object_name == 'Lead'
    assert not new_job.job
    assert not new_job.is_open
    assert not new_job.job_url
    assert not new_job.pending_batches

    assert salesforce_session.call_count == 1
    assert bulk_request.call_count == 0

def test_instantiating_salesforce_bulk_job_validates_operation(salesforce_session, bulk_request):
    """Instantiating a SalesforceBulkJob should validate the requested operation"""
    with pytest.raises(AssertionError):
        SalesforceBulkJob('floob', 'Lead')

def test_instantiating_salesforce_bulk_job_validates_object(salesforce_session, bulk_request):
    """Instantiating a SalesforceBulkJob should validate the requested object"""
    with pytest.raises(AssertionError):
        SalesforceBulkJob('update', 'lead')
    with pytest.raises(AssertionError):
        SalesforceBulkJob('update', 'Floob')

def test_upload_orchestration(new_job):
    """The SalesforceBulkJob.upload method should simply orchestrate the other
    methods as a convenience."""
    with mock.patch.object(new_job, 'create') as create, \
         mock.patch.object(new_job, 'add_batch') as add_batch, \
         mock.patch.object(new_job, 'abort') as abort, \
         mock.patch.object(new_job, 'close') as close, \
         mock.patch.object(new_job, 'wait') as wait:

        def add_a_batch_for_real(*args, **kwargs):
            new_job.pending_batches = new_job.pending_batches or []
            new_job.pending_batches.append('FAKE ONE')
        add_batch.side_effect = add_a_batch_for_real

        new_job.upload(['Id', 'Description'], [[1, 2], [3, 4]])

        create.assert_called_once_with()
        add_batch.assert_called_once_with(['Id', 'Description'], [[1, 2], [3, 4]])
        assert abort.call_count == 0
        close.assert_called_once_with()
        wait.assert_called_once_with()

def test_upload_orchestration_no_batches(new_job):
    """The SalesforceBulkJob.upload method should gracefully abort a job if it
    turns out to have no batches"""
    with mock.patch.object(new_job, 'create') as create, \
         mock.patch.object(new_job, 'add_batch') as add_batch, \
         mock.patch.object(new_job, 'abort') as abort, \
         mock.patch.object(new_job, 'close') as close, \
         mock.patch.object(new_job, 'wait') as wait:

        new_job.upload(['Id', 'Description'], [])

        create.assert_called_once_with()
        assert add_batch.call_count == 0
        abort.assert_called_once_with()
        assert close.call_count == 0
        assert wait.call_count == 0


@pytest.fixture()
def created_job(new_job, bulk_request):
    """Prepares a job with ID 'THEJOBID' which has already been created"""
    bulk_request.return_value = '''<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>THEJOBID</id>
            <operation>update</operation>
            <object>Lead</object>
        </jobInfo>
    '''
    new_job.create()
    return new_job

def test_creating_a_job(created_job, bulk_request):
    """Creating a job should set the internal state properly"""
    assert created_job.job == 'THEJOBID'
    assert created_job.job_url == 'https://salesforce/services/async/34.0/job/THEJOBID'
    assert created_job.pending_batches == []
    assert created_job.is_open

    bulk_request.assert_called_once_with(
        'post',
        'https://salesforce/services/async/34.0/job',
        data=XMLMatcher('''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <operation>update</operation>
                <object>Lead</object>
                <contentType>CSV</contentType>
            </jobInfo>
        ''')
    )

@pytest.fixture()
def upsert_job(new_job, bulk_request):
    """Prepares a job with ID 'THEJOBID' which has already been created"""
    return SalesforceBulkJob('upsert', 'Lead', external_id_field='The_External_ID__c')

def test_creating_an_upsert_job(upsert_job, bulk_request):
    bulk_request.return_value = '''<?xml version="1.0" encoding="UTF-8"?>
        <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>THEJOBID</id>
            <operation>upsert</operation>
            <object>Lead</object>
        </jobInfo>
    '''
    upsert_job.create()
    bulk_request.assert_called_once_with(
        'post',
        'https://salesforce/services/async/34.0/job',
        data=XMLMatcher('''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <operation>upsert</operation>
                <object>Lead</object>
                <externalIdFieldName>The_External_ID__c</externalIdFieldName>
                <contentType>CSV</contentType>
            </jobInfo>
        ''')
    )

def test_adding_a_batch(created_job, bulk_request):
    """Adding a batch should upload a CSV representation of the data to the job"""
    bulk_request.reset_mock()
    bulk_request.return_value = '''<?xml version="1.0" encoding="UTF-8"?>
        <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            <id>BATCHONE</id>
            <jobId>THEJOBID</jobId>
            <state>Queued</state>
        </batchInfo>
    '''

    fake_data = [('1', '2'), ('3', '4')]
    created_job.add_batch(['Id', 'Name'], iter(fake_data))

    assert created_job.pending_batches == ['BATCHONE']

    bulk_request.assert_called_once_with(
        'post',
        'https://salesforce/services/async/34.0/job/THEJOBID/batch',
        content_type='text/csv; charset=UTF-8',
        data=mock.ANY
    )

    data = bulk_request.call_args[1]['data']
    assert b''.join(data) == b'Id,Name\r\n1,2\r\n3,4\r\n'

def test_closing_batch(created_job, bulk_request):
    """Closing a batch should set the internal state appropriately"""
    bulk_request.reset_mock()

    assert created_job.is_open

    created_job.close()

    assert not created_job.is_open
    assert created_job.job == 'THEJOBID'

    bulk_request.assert_called_once_with(
        'post',
        'https://salesforce/services/async/34.0/job/THEJOBID',
        data=XMLMatcher('''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <state>Closed</state>
            </jobInfo>
        '''),
        expected_response=200
    )

def test_aborting_batch(created_job, bulk_request):
    """Aborting a batch should set the internal state appropriately"""
    bulk_request.reset_mock()

    assert created_job.is_open

    created_job.abort()

    assert not created_job.job
    assert not created_job.job_url
    assert not created_job.pending_batches
    assert not created_job.is_open

    bulk_request.assert_called_once_with(
        'post',
        'https://salesforce/services/async/34.0/job/THEJOBID',
        data=XMLMatcher('''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <state>Aborted</state>
            </jobInfo>
        '''),
        expected_response=200
    )


@pytest.fixture()
def closed_job(created_job, bulk_request):
    """Prepares a job which has had two batches added to it, and has been closed"""
    bulk_request.side_effect = [
        '''<?xml version="1.0" encoding="UTF-8"?>
            <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <id>BATCHONE</id>
            </batchInfo>
        ''',
        '''<?xml version="1.0" encoding="UTF-8"?>
            <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
                <id>BATCHTWO</id>
            </batchInfo>
        ''',
        '''<?xml version="1.0" encoding="UTF-8"?>
            <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
            </batchInfo>
        ''',
    ]
    created_job.add_batch(['Id', 'Description'], [[1, 2], [3, 4]])
    created_job.add_batch(['Id', 'Description'], [[5, 6], [7, 8]])
    created_job.close()
    return created_job

def test_waiting(closed_job, bulk_request):
    """Waiting for a job should wait for all of its batches to finish in any state"""
    assert closed_job.pending_batches == ['BATCHONE', 'BATCHTWO']

    bulk_request.reset_mock()
    bulk_request.side_effect = [
        '''<?xml version="1.0" encoding="UTF-8"?>
           <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
               <state>Completed</state>
               <id>BATCHONE</id>
           </batchInfo>''',
        '''<?xml version="1.0" encoding="UTF-8"?>
           <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
               <state>InProgress</state>
               <id>BATCHTWO</id>
           </batchInfo>''',
        '''<?xml version="1.0" encoding="UTF-8"?>
           <batchInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">
               <state>Completed</state>
               <id>BATCHTWO</id>
           </batchInfo>''',
    ]

    with mock.patch('salesforce_bulk_api.time.sleep') as sleep:
        closed_job.wait()
        sleep.assert_called_once_with(10)

    bulk_request.assert_has_calls([
        mock.call('get', 'https://salesforce/services/async/34.0/job/THEJOBID/batch/BATCHONE', expected_response=200),
        mock.call('get', 'https://salesforce/services/async/34.0/job/THEJOBID/batch/BATCHTWO', expected_response=200),
        mock.call('get', 'https://salesforce/services/async/34.0/job/THEJOBID/batch/BATCHTWO', expected_response=200),
    ])

    assert closed_job.pending_batches == []
    assert closed_job.finished_batches == ['BATCHONE', 'BATCHTWO']

@pytest.fixture
def finished_job(closed_job):
    assert closed_job.pending_batches == ['BATCHONE', 'BATCHTWO']
    closed_job.pending_batches = []
    closed_job.finished_batches = ['BATCHONE', 'BATCHTWO']
    return closed_job

def test_getting_results(finished_job, bulk_request):
    bulk_request.reset_mock()
    bulk_request.side_effect = [
        b'\n'.join([b'Id,Success,Created,Error',
                    b'New,true,true,',
                    b'Old,true,false,',
                    b'Fail,false,false,bad things went down']),
        b'\n'.join([b'Id,Success,Created,Error',
                    b'Another,true,true,'])
    ]

    results = list(finished_job.results())
    assert results == [
        ('New', True, True, ''),
        ('Old', True, False, ''),
        ('Fail', False, False, 'bad things went down'),
        ('Another', True, True, '')
    ]


@pytest.yield_fixture()
def httpretty():
    """Prepares the httpretty module for the HTTP tests in this suite"""
    import httpretty
    httpretty.enable()
    yield httpretty
    httpretty.disable()

def test_api_authentication(httpretty, new_job):
    """Requests should include a Salesforce session ID for authentication"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('GET', url, status=200)
    new_job.request('get', url, expected_response=200)
    assert httpretty.last_request().headers['X-SFDC-Session'] == 'the-session-id'

def test_api_content_type(httpretty, new_job):
    """Requests should include the specified Content-Type for the supplied data"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('POST', url, status=201)
    new_job.request('post', url, data=b'hi', content_type='text/plain')
    assert httpretty.last_request().headers['Content-Type'] == 'text/plain'

def test_api_default_content_type(httpretty, new_job):
    """Requests should include the default Content-Type of application/xml"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('POST', url, status=201)
    new_job.request('post', url, data=b'hi')
    assert httpretty.last_request().headers['Content-Type'] == 'application/xml; charset=UTF-8'

def test_api_get(httpretty, new_job):
    """Requests should support HTTP GET requests"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('GET', url, status=200, body=b'some xml and stuff')
    response = new_job.request('get', url, expected_response=200)
    assert response == b'some xml and stuff'

def test_api_post(httpretty, new_job):
    """Requests should support HTTP POST requests"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('POST', url, status=201, body=b'some xml and stuff')
    response = new_job.request('post', url, data=b'stuff')
    assert response == b'some xml and stuff'
    assert httpretty.last_request().body == b'stuff'

def test_api_requests_error_status(httpretty, new_job):
    """Requests should not retry when receiving an error status code"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri('GET', url, status=500, body=b'some xml and stuff')
    with pytest.raises(Exception) as e:
        with mock.patch('salesforce_bulk_api.time.sleep') as sleep:
            new_job.request('get', url, expected_response=200)
    assert sleep.call_count == 0
    assert 'Unexpected status 500' in str(e)

def test_api_requests_server_unavailable_status(httpretty, new_job):
    """Requests should retry when receiving a status code indicating an outage"""
    url = 'https://salesforce/services/async/34.0/job/THEJOBID'
    httpretty.register_uri(
        'GET', url,
        responses=[
            httpretty.Response(status=502, body=b'some xml and stuff'),
            httpretty.Response(status=503, body=b'some xml and stuff'),
            httpretty.Response(status=502, body=b'some xml and stuff')
        ]
    )
    with pytest.raises(Exception) as e:
        with mock.patch('salesforce_bulk_api.time.sleep') as sleep:
            new_job.request('get', url, expected_response=200)
    assert sleep.call_count == 2
    assert 'Unexpected status 502' in str(e)

def test_api_requests_server_connect_errors(httpretty, new_job):
    """Requests should retry when receiving a connection-related error"""
    url = 'https://nowhere/services/async/34.0/job/THEJOBID'
    with pytest.raises(requests.exceptions.ConnectionError) as e:
        with mock.patch('salesforce_bulk_api.time.sleep') as sleep:
            new_job.request('get', url, expected_response=200)
    assert sleep.call_count == 2
    assert 'Connection aborted' in str(e)
