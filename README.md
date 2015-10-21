salesforce_bulk_api
===================

This library provides a simple wrapper to the [Salesforce Bulk API](https://developer.salesforce.com/docs/atlas.en-us.api_asynch.meta/api_asynch/),
which offers a very fast method to create, update, delete, or even upsert large
numbers of Salesforce records asynchronously.

Installation
============

`salesforce_bulk_api` has been testing on Python 2.7, 3.1, 3.3, 3.4, and pypy.
At runtime, it depends on [requests](http://docs.python-requests.org/en/latest/)
and [simple_salesforce](https://github.com/heroku/simple-salesforce) (to handle
authentication).

```
$ pip install salesforce_bulk_api
```

Usage
=====

```
from salesforce_bulk_api import SalesforceBulkJob

job = SalesforceBulkJob('update', 'Contact')
job.upload(
    ['Id', 'FirstName', 'LastName', 'Your_Custom_Field__c'],
    [
        ('CONTACT-1', 'Hello', 'World', 'My Custom Value'),
        ('CONTACT-2', 'Goodbye', 'Moon', 'Another Custom Value'),
        ....
    ]
)
```

The arguments to create a `SalesforceBulkJob` are the action ('create',
'update', 'delete', 'upsert') and the Salesforce object name (like 'Lead' or
'Contact' or 'Opportunity').

The first argument to `upload` is a list of column headers, using the Salesforce
technical field names for the object.  You can find these in your Salesforce
under "Setup" -> "Customize" -> The Object Type.

The second argument to `upload` is *any iterable* (you can use a generator to
keep your memory usage lower!) of `tuple`s containing the field values.

`SalesforceBulkJob` will split your input into batches, upload them to Salesforce,
and wait for all of the batches to successfully complete.  If you are interested
in the results, you can make a call to `.results()` after your initial call to
`.upload()`.

Logging
=======

Because the upload to Salesforce is a fairly complicated operation, this library
performs extensive INFO-level logging to the logger named 'salesforce_bulk_api'.
You may want to turn this level up or down depending on your needs and your
logging configuration.


Authentication with Salesforce
==============================

`salesforce_bulk_api` is configured with environment variables, which you can
provide externally to running your Python program, or by setting keys in
`os.environ`.  The variables are as follows:

```
SALESFORCE_INSTANCE=...the domain name of your Salesforce instance, like abc123.salesforce.com...
SALESFORCE_SANDBOX=...the string "True" or "False", indicating whether this is a Salesforce sandbox instance...
SALESFORCE_USERNAME=...a valid Salesforce user with permissions to create and manage bulk jobs...
SALESFORCE_PASSWORD=...the Salesforce user's password...
SALESFORCE_SECURITY_TOKEN=...the Salesforce user's security token (which you get from the Salesforce user interface)...
```


License
=======

Licensed under the BSD 3-clause license.

> Copyright (c) 2015, Safari Books Online
> All rights reserved.
>
> Redistribution and use in source and binary forms, with or without
> modification, are permitted provided that the following conditions are met:
> * Redistributions of source code must retain the above copyright
>   notice, this list of conditions and the following disclaimer.
> * Redistributions in binary form must reproduce the above copyright
>   notice, this list of conditions and the following disclaimer in the
>   documentation and/or other materials provided with the distribution.
> * Neither the name of the Safari Books Online nor the
>   names of its contributors may be used to endorse or promote products
>   derived from this software without specific prior written permission.
>
> THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
> ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
> WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
> DISCLAIMED. IN NO EVENT SHALL Safari Books Online BE LIABLE FOR ANY
> DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
> (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
> LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
> ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
> (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
> SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
