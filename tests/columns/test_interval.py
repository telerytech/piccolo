import datetime
from unittest import TestCase

from piccolo.table import Table
from piccolo.columns.column_types import Interval
from piccolo.columns.defaults.interval import IntervalCustom


class MyTable(Table):
    interval = Interval()


class MyTableDefault(Table):
    interval = Interval(default=IntervalCustom(days=1))


class TestInterval(TestCase):
    def setUp(self):
        MyTable.create_table().run_sync()

    def tearDown(self):
        MyTable.alter().drop_table().run_sync()

    def test_interval(self):
        interval = datetime.timedelta(hours=2)
        row = MyTable(interval=interval)
        row.save().run_sync()

        result = MyTable.objects().first().run_sync()
        self.assertEqual(result.interval, interval)


class TestIntervalDefault(TestCase):
    def setUp(self):
        MyTableDefault.create_table().run_sync()

    def tearDown(self):
        MyTableDefault.alter().drop_table().run_sync()

    def test_interval(self):
        row = MyTableDefault()
        row.save().run_sync()

        result = MyTableDefault.objects().first().run_sync()
        self.assertTrue(result.interval.days == 1)