# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-01-13 08:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0078_merge_20211230_1614"),
    ]

    operations = [
        migrations.AddField(
            model_name="metricmappingconfigmodel",
            name="range_type",
            field=models.CharField(default="kubernetes", max_length=128, verbose_name="数据范围类型"),
        ),
    ]