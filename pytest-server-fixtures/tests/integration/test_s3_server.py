# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals


def test_connection(s3_bucket):
    client, bucket_name = s3_bucket
    bucket = client.Bucket(bucket_name)
    assert bucket is not None
