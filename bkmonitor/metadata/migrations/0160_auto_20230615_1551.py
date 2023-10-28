# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2023-06-15 07:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0159_auto_20230606_2140'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downsamplebydateflow',
            name='hdfs_cluster',
            field=models.CharField(default='hdfsOnline4', max_length=32, verbose_name='离线计算使用的存储集群'),
        ),
        migrations.AlterField(
            model_name='pingserversubscriptionconfig',
            name='bk_host_id',
            field=models.IntegerField(db_index=True, default=None, null=True, verbose_name='主机ID'),
        ),
    ]