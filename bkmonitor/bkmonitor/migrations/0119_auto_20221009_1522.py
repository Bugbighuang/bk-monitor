# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-10-09 07:22
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0118_merge_20221009_1508"),
    ]

    operations = [
        migrations.AddField(
            model_name="metriclistcache",
            name="readable_name",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="指标可读名", db_index=True),
        ),
    ]