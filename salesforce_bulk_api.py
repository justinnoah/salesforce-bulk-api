# encoding: utf-8
#
# Copyright (c) 2015 Safari Books Online. All rights reserved.
#
# This software may be modified and distributed under the terms
# of the 3-clause BSD license.  See the LICENSE file for details.

from __future__ import unicode_literals, with_statement

import csv
from datetime import datetime, timedelta
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        from io import StringIO
from itertools import chain
import logging
import os
import time
from xml.etree import ElementTree

import requests
from simple_salesforce import Salesforce

logger = logging.getLogger('salesforce-bulk-api')

NAMESPACE = 'http://www.force.com/2009/06/asyncapi/dataload'


def salesforce_session():
    """Returns an authenticated simple_salesforce.Salesforce instance."""
    return Salesforce(username=os.environ['SALESFORCE_USERNAME'],
                      password=os.environ['SALESFORCE_PASSWORD'],
                      security_token=os.environ['SALESFORCE_SECURITY_TOKEN'],
                      instance=os.environ['SALESFORCE_INSTANCE'],
                      sandbox=os.environ.get('SALESFORCE_SANDBOX') == 'True',
                      version='34.0')


class SalesforceBulkJob:
    """A Python interface to the Salesforce Bulk API."""

    PUBLISHING_BATCH_SIZE = 9999
    SUPPORTED_OPERATIONS = {'insert', 'update', 'delete', 'upsert'}

    def __init__(self, operation, object_name, external_id_field=None):
        """Creates a new API interface to Salesforce's bulk API, from which any
        number of jobs may be created.  The operation should be one of ('insert',
        'update', 'upsert', or 'delete'), and the object_name should be the
        proper-case name of a Salesforce object (like Lead or Contact)."""
        salesforce = salesforce_session()
        self.session_id = salesforce.session_id
        self.async_url = (salesforce.base_url
                                    .replace('/data/', '/async/')
                                    .replace('v' + salesforce.sf_version,
                                             salesforce.sf_version))

        assert operation in self.SUPPORTED_OPERATIONS, '{} is not a valid bulk operation.'.format(operation)
        self.operation = operation

        supported_objects = {o['name'] for o in salesforce.describe()['sobjects']}
        assert object_name in supported_objects, '{} is not a known Salesforce object.'.format(object_name)
        self.object_name = object_name
        self.external_id_field = external_id_field

        self.reset()

    def upload(self, fields, data):
        """Given a list of fields and a (potentially very long) iterable of
        tuples matching those fields, perform a complete upload to Salesforce"""
        self.create()
        for chunk in chunked(data, self.PUBLISHING_BATCH_SIZE):
            if chunk:
                self.add_batch(fields, chunk)
        if not self.pending_batches:
            logger.info('No batches added to job.')
            self.abort()
            return
        self.close()
        self.wait()

    def create(self):
        """Creates a new Salesforce bulk Job and prepares for adding batches."""
        assert not self.job, 'The current job is still open.'

        logger.info('Creating new job to %s %s', self.operation, self.object_name)
        job_request = '''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="{NAMESPACE}">
                <operation>{operation}</operation>
                <object>{object_name}</object>
        '''

        if self.operation == 'upsert':
            job_request += '<externalIdFieldName>{external_id_field}</externalIdFieldName>'

        job_request += '''
                <contentType>CSV</contentType>
            </jobInfo>
        '''

        job_request = job_request.format(
            NAMESPACE=NAMESPACE,
            object_name=self.object_name,
            operation=self.operation,
            external_id_field=self.external_id_field
        )
        response = self.request('post', self.async_url + 'job',
                                data=job_request)

        self.job = bulk_response_attribute(response, 'id')
        self.job_url = self.async_url + 'job/' + self.job
        self.pending_batches = []
        self.is_open = True

    def add_batch(self, fields, data):
        """Given a list of fields and an iterable of tuples matching those
        fields, adds a batch of data to the current job.  The data must be
        shorter than PUBLISHING_BATCH_SIZE rows"""
        assert self.job, 'There is no current job.'
        assert self.is_open, 'The current job is not open.'

        logger.info('Adding batch to job %s', self.job_url)
        response = self.request('post', self.job_url + '/batch',
                                data=itercsv(fields, data),
                                content_type='text/csv; charset=UTF-8')
        batch = bulk_response_attribute(response, 'id')
        self.pending_batches.append(batch)

    def close(self):
        """Closes the current job, which signals to Salesforce that no further
        batches will be added to it."""
        logger.info('Closing job %s', self.job_url)
        self.set_job_state('Closed')
        self.is_open = False

    def abort(self):
        """Aborts the current job, and resets the instance"""
        logger.info('Aborting job %s', self.job_url)
        self.set_job_state('Aborted')
        self.reset()

    def set_job_state(self, state):
        """Sets the current job to the given state ("Closed" or "Aborted")"""
        assert self.job, 'There is no current job.'
        assert self.is_open, 'The current job is not open.'

        state_request = '''<?xml version="1.0" encoding="UTF-8"?>
            <jobInfo xmlns="{NAMESPACE}">
              <state>{state}</state>
            </jobInfo>
        '''.format(NAMESPACE=NAMESPACE, state=state)
        self.request('post', self.job_url, data=state_request, expected_response=200)

    def wait(self):
        """Waits for all batches of the current job to finish"""
        assert self.job, 'There is no current job.'
        assert not self.is_open, 'The current job must be closed before waiting.'

        self.finished_batches = []
        total = len(self.pending_batches)
        while self.pending_batches:
            finished = []
            for i, batch in enumerate(self.pending_batches):
                batch_url = self.job_url + '/batch/' + batch
                response = self.request('get', batch_url, expected_response=200)
                state = bulk_response_attribute(response, 'state')
                if state not in {'Queued', 'InProgress'}:
                    finished.append(i)
                    log_method = (logger.warn
                                  if state in {'Failed', 'Not Processed'}
                                  else logger.info)
                    log_method('Batch %s (%s/%s) finished with state %s',
                               batch_url, total - len(self.pending_batches) + len(finished), total, state)

            for i in sorted(finished, reverse=True):
                self.finished_batches.append(self.pending_batches.pop(i))

            if self.pending_batches:
                logger.info('Waiting for %s more batches to complete...', len(self.pending_batches))
                time.sleep(10)

    def results(self):
        assert self.job, 'There is no current job.'
        assert not self.is_open, 'The current job must be closed before getting results.'
        assert self.finished_batches is not None, 'SalesforceBulkJob.wait() should be called before getting results.'

        for batch in self.finished_batches:
            result_url = self.job_url + '/batch/' + batch + '/result'
            response = self.request('get', result_url, expected_response=200)
            reader = csv.reader(StringIO(response.decode('utf-8')))
            next(reader)  # consume the header row
            for id, success, created, error in reader:
                yield id, success == 'true', created == 'true', error

    def reset(self):
        """Resets the state of this job to that of a new instance.  This *does
        not* change anything that has happened so far at Salesforce.  See
        `.abort()` to cancel the currently open job."""
        self.is_open = False
        self.job = self.job_url = self.pending_batches = self.finished_batches = None

    def request(self, method, url,
                data=None,
                content_type='application/xml; charset=UTF-8',
                expected_response=201):
        """Performs an HTTP request against Salesforce's bulk API, and validates
        the expected response.  Returns the content of the response"""

        headers = {'X-SFDC-Session': self.session_id}
        kwargs = {'headers': headers}
        if data is not None:
            headers['Content-Type'] = content_type
            kwargs['data'] = data

        RETRIES, LAST, WAIT = 3, 2, timedelta(seconds=5)
        for retry in range(RETRIES):
            try:
                response = getattr(requests, method)(url, **kwargs)
            except requests.exceptions.ConnectionError:
                if retry == LAST:
                    raise
                logger.info('ConnectionError from %r %r.  Retrying in %r...',
                            method, url, WAIT, exc_info=True)
            else:
                if retry < LAST and response.status_code in (502, 503):
                    logger.info('%r response from %r %r.  Retrying in %r...',
                                response.status_code, method, url, WAIT)
                else:
                    break
            time.sleep(WAIT.total_seconds())

        if response.status_code != expected_response:
            raise Exception(('Unexpected status {} from '
                             'Salesforce async API.  Details: {}'
                            ).format(response.status_code, response.content))
        return response.content


def bulk_response_attribute(response, attribute):
    """Given a Salesforce bulk API response bytes, and the name of an attribute,
    find it in the given document, or raise if it isn't present"""
    tree = ElementTree.fromstring(response)
    value = tree.findtext('{{{}}}{}'.format(NAMESPACE, attribute))
    if not value:
        raise Exception(('<{}> not found in Salesforce '
                         'async API response.  Response: {}'
                        ).format(attribute, response))
    return value


def chunked(iterable, size):
    """Yields chunks of the requested size from the iterable.  The final chunk
    may be smaller than size"""
    if not size:
        for item in iterable:
            yield item
        return

    chunk = []
    for i, item in enumerate(iterable):
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

def itercsv(headers, data):
    """Given a list of headers name and a (potentially large) iterable of
    tuples, yield the lines of a CSV file representing that data"""
    buffer = StringIO()
    writer = csv.writer(buffer)

    for row in chain([headers], data):
        writer.writerow(row)
        buffer.seek(0)
        yield buffer.read().encode('utf-8')
        buffer.truncate(0)
        buffer.seek(0)
