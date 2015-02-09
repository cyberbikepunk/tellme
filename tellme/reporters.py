# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import yaml
import dataset
from . import compat
from . import encoders
from . import exceptions


class Report(object):

    """Create, manage and output informational reports from Python."""

    REPORT_FORMATS = ('dict', 'json', 'yaml', 'csv', 'html')
    REPORT_BACKENDS = ('sql', 'yaml')
    FILE_BACKENDS = ('yaml',)

    def __init__(self, name='report', schema=None, template=None,
                 backend='yaml', storage_path=None):

        self.name = name
        self.meta = {
            'name': self.name
        }
        self.template = template
        self.schema = schema
        self.backend = backend

        if self.backend not in self.REPORT_BACKENDS:
            raise ValueError

        elif self.backend in self.FILE_BACKENDS:
            if storage_path:
                self.storage = io.open(storage_path, mode='a+t',
                                       encoding='utf-8')
            else:
                self.storage = compat.NamedTemporaryFile(mode='a+t',
                                                         encoding='utf-8')
            if self.backend == 'yaml':
                # valid YAML documents should start with '---'
                self.storage.write('---\n')

        elif self.backend == 'sql':
            storage_path = storage_path or 'sqlite:///:memory:'
            db = dataset.connect(storage_path)
            self.storage = db['{0}_data'.format(self.name)]

        else:
            raise NotImplementedError

    def write(self, entry):
        """Write an entry to the report."""
        if self._validate_entry(entry):
            return getattr(self, 'write_{0}'.format(self.backend))(entry)
        else:
            raise exceptions.InvalidEntryError

    def write_yaml(self, entry):
        """Write an entry to a YAML backend."""
        return self.storage.write(yaml.dump([entry], default_flow_style=False))

    def write_sql(self, entry):
        """Write an entry to an SQLite backend."""
        self.storage.insert(entry)

    def multi_write(self, entries):
        """Write multiple entries at once."""
        for entry in entries:
            self.write(entry)
        return True

    def read(self):
        return getattr(self, 'read_{0}'.format(self.backend))()

    def read_yaml(self):
        """Read all data from a YAML backend."""
        self.storage.seek(0)
        return yaml.load(self.storage.read())

    def read_sql(self):
        """Read all data from an SQLite backend."""
        return [result for result in self.storage.all()]

    def close(self):
        """Close the backend storage."""
        if self.backend in self.FILE_BACKENDS:
            return self.close_file()

    def close_file(self):
        """Close backend file."""
        return self.storage.close()

    def generate(self, format='dict'):
        """Generate a report for this validator."""

        if format not in self.REPORT_FORMATS:
            raise ValueError
        else:
            rv = getattr(self, 'generate_{0}'.format(format))()
            self.close()
            return rv

    def generate_dict(self):
        """Generate a report as a Python dictionary."""
        return {
            'meta': self.meta,
            'data': self.read()
        }

    def generate_json(self):
        """Generate a report as JSON."""
        return json.dumps(self.generate_dict(), cls=encoders.ReportJSONEncoder)

    def generate_csv(self):
        """Generate a report as CSV."""
        raise NotImplementedError

    def generate_html(self):
        """Generate a report as HTML."""
        raise NotImplementedError

    def _validate_entry(self, entry):
        """Validate the entry against the schema."""

        if self.schema is None:
            return True

        for k, v in entry.items():
            if k not in self.schema.keys():
                return False
            if not isinstance(v, self.schema[k]['type']):
                return False

        return True