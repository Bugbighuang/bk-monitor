# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2023-03-01 08:40
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0144_auto_20230224_1432'),
    ]

    operations = [
        migrations.AddField(
            model_name='clusterinfo',
            name='batch_size',
            field=models.IntegerField(default=None, null=True, verbose_name='批量写入的大小'),
        ),
        migrations.AddField(
            model_name='clusterinfo',
            name='consume_rate',
            field=models.IntegerField(default=None, null=True, verbose_name='消费速率'),
        ),
        migrations.AddField(
            model_name='clusterinfo',
            name='flush_interval',
            field=models.CharField(default=None, max_length=16, null=True, verbose_name='写入间隔'),
        ),
    ]