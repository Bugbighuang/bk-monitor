# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2021-11-09 12:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0098_merge_20211027_1132"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bcsclusterinfo",
            name="bk_biz_id",
            field=models.IntegerField(db_index=True, verbose_name="业务ID"),
        ),
        migrations.AlterField(
            model_name="bcsclusterinfo",
            name="cluster_id",
            field=models.CharField(db_index=True, max_length=128, verbose_name="集群ID"),
        ),
    ]