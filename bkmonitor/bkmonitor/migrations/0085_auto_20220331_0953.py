# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-03-31 01:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0084_merge_20220330_1611"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dutyplan",
            name="id",
            field=models.BigAutoField(primary_key=True, serialize=False, verbose_name="主键"),
        ),
    ]